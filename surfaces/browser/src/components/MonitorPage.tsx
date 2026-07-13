import React, { useState, useEffect, useRef } from 'react';
import {
  VideoCamera, Camera, UploadSimple, Play, Stop, Trash, GearSix,
  ArrowLineDownLeft, ArrowLineUpRight, FileText, Plus, Plugs, Users,
  SlidersHorizontal, X, Pencil,
} from '@phosphor-icons/react';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../hooks/useToast';
import { readThemeColors } from '../hooks/useTheme';

const ICON = { size: 16, weight: 'regular' as const };
const ICON_SM = { size: 14, weight: 'regular' as const };
const CAPTURE_WIDTH = 640;
const CAPTURE_HEIGHT = 480;
const JPEG_QUALITY = 0.65;
const TARGET_FRAME_INTERVAL_MS = 66;
const DETECTION_INTERVAL_FRAMES = 3;
const INITIAL_DETECTION_FRAMES = 2;
const IDENTITY_PROBE_INTERVAL_FRAMES = 8;
const INITIAL_IDENTITY_PROBE_FRAMES = 3;
const IDENTITY_TTL_SECONDS = 5;

interface Track {
  track_id: number;
  bbox: [number, number, number, number];
  confidence: number;
  person_name?: string;
  identity_type?: 'KNOWN' | 'UNKNOWN' | 'UNRESOLVED';
  similarity_score?: number;
  predicted?: boolean;
  lost?: number;
}

interface CrossingEvent {
  track_id: number;
  direction: 'ENTRY' | 'EXIT';
  timestamp: number;
  person_name?: string;
  identity_type?: 'KNOWN' | 'UNKNOWN' | 'UNRESOLVED';
  similarity_score?: number;
}

interface LogItem {
  id: string;
  time: string;
  text: string;
  type: 'entry' | 'exit' | 'system';
}

type CameraSourceTab = 'webcam' | 'upload' | 'rtsp';
type LogFilter = 'all' | 'entry' | 'exit' | 'system';

export function MonitorPage() {
  const { apiUrl } = useAuth();
  const { show: showToast } = useToast();

  const [cameraSourceTab, setCameraSourceTab] = useState<CameraSourceTab>('webcam');
  const [backendUrl, setBackendUrl] = useState(apiUrl);
  const [isBackendOnline, setIsBackendOnline] = useState(false);
  const [sourceType, setSourceType] = useState<'webcam' | 'video' | 'none'>('none');
  const [isRunning, setIsRunning] = useState(false);
  const [fps, setFps] = useState(0);
  const [responseLatencyMs, setResponseLatencyMs] = useState(0);
  const [activeTracksCount, setActiveTracksCount] = useState(0);
  const [entriesCount, setEntriesCount] = useState(0);
  const [exitsCount, setExitsCount] = useState(0);
  const [logs, setLogs] = useState<LogItem[]>([]);
  const [logFilter, setLogFilter] = useState<LogFilter>('all');
  const [showBboxes, setShowBboxes] = useState(true);
  const [showLine, setShowLine] = useState(true);
  const [showTrackIds, setShowTrackIds] = useState(true);
  const [lineConfig, setLineConfig] = useState<[[number, number], [number, number]]>([[320, 0], [320, 480]]);
  const [isDrawing, setIsDrawing] = useState(false);
  const [animateEntry, setAnimateEntry] = useState(false);
  const [animateExit, setAnimateExit] = useState(false);
  const [videoFlash, setVideoFlash] = useState<'entry' | 'exit' | null>(null);
  const [camerasList, setCamerasList] = useState<{ id: number; name: string; source_url: string; status: string }[]>([]);
  const [newCamName, setNewCamName] = useState('');
  const [newCamUrl, setNewCamUrl] = useState('');
  const [editingCamId, setEditingCamId] = useState<number | null>(null);
  const [editCamName, setEditCamName] = useState('');
  const [editCamUrl, setEditCamUrl] = useState('');

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const overlayCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const loopTimeoutRef = useRef<number | null>(null);
  const sessionTrackerIdRef = useRef<string>(`session_${Math.floor(Date.now() / 1000)}`);
  const streamRef = useRef<MediaStream | null>(null);
  const lastFrameTimeRef = useRef<number>(0);
  const isRunningRef = useRef(false);
  const frameSequenceRef = useRef(0);
  const processedFramesRef = useRef(0);

  const apiUrlFn = (path: string) => {
    const base = backendUrl.trim().replace(/\/$/, '');
    const suffix = path.startsWith('/') ? path : `/${path}`;
    return `${base}${suffix}`;
  };

  useEffect(() => {
    let active = true;
    const checkHealth = async () => {
      try {
        const res = await fetch(`${apiUrlFn('/api/health')}`);
        if (active) setIsBackendOnline(res.ok);
      } catch {
        if (active) setIsBackendOnline(false);
      }
    };
    checkHealth();
    const interval = setInterval(checkHealth, 5000);
    return () => { active = false; clearInterval(interval); };
  }, [backendUrl]);

  useEffect(() => {
    stopPipeline();
    clearOverlayCanvas();
  }, [sourceType]);

  useEffect(() => {
    loadCameras();
  }, [backendUrl]);

  useEffect(() => {
    clearOverlayCanvas();
  }, [lineConfig, sourceType, showLine]);

useEffect(() => {
  return () => {
    isRunningRef.current = false;
    if (loopTimeoutRef.current !== null) {
      clearTimeout(loopTimeoutRef.current);
      loopTimeoutRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
  };
}, []);
  const loadCameras = async () => {
    try {
      const res = await fetch(`${apiUrlFn('/api/cameras')}`);
      if (res.ok) {
        const data = await res.json();
        setCamerasList(data.items || data || []);
      }
    } catch (err) { console.error('Failed to load cameras:', err); }
  };

  const handleAddCamera = async () => {
    if (!newCamName || !newCamUrl) {
      showToast('Vui lòng nhập tên camera và địa chỉ kết nối.', 'error');
      return;
    }
    try {
      const res = await fetch(`${apiUrlFn('/api/cameras')}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newCamName, source_type: 'RTSP', source_url: newCamUrl }),
      });
      if (res.ok) {
        showToast('Đã thêm camera mạng.', 'success');
        setNewCamName('');
        setNewCamUrl('');
        loadCameras();
      } else {
        const err = await res.json();
        showToast(`Thêm camera thất bại: ${err.detail || 'Lỗi không xác định'}`, 'error');
      }
    } catch {
      showToast('Không thể kết nối đến máy chủ API.', 'error');
    }
  };

  const handleRemoveCamera = async (id: number, name: string) => {
    if (!confirm(`Xoá camera "${name}"?`)) return;
    try {
      const res = await fetch(`${apiUrlFn(`/api/cameras/${id}`)}`, { method: 'DELETE' });
      if (res.ok) {
        showToast(`Đã xoá camera "${name}".`, 'success');
        loadCameras();
      } else {
        const err = await res.json();
        showToast(`Xoá thất bại: ${err.detail || 'Lỗi'}`, 'error');
      }
    } catch {
      showToast('Không thể kết nối đến máy chủ API.', 'error');
    }
  };

  const startEdit = (cam: { id: number; name: string; source_url: string }) => {
    setEditingCamId(cam.id);
    setEditCamName(cam.name);
    setEditCamUrl(cam.source_url);
  };

  const cancelEdit = () => {
    setEditingCamId(null);
    setEditCamName('');
    setEditCamUrl('');
  };

  const handleUpdateCamera = async () => {
    if (!editCamName.trim() || !editCamUrl.trim()) {
      showToast('Vui lòng nhập đầy đủ thông tin.', 'error');
      return;
    }
    try {
      const res = await fetch(`${apiUrlFn(`/api/cameras/${editingCamId}`)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: editCamName.trim(), source_type: 'RTSP', source_url: editCamUrl.trim() }),
      });
      if (res.ok) {
        showToast('Đã cập nhật camera.', 'success');
        cancelEdit();
        loadCameras();
      } else {
        const err = await res.json();
        showToast(`Cập nhật thất bại: ${err.detail || 'Lỗi'}`, 'error');
      }
    } catch {
      showToast('Không thể kết nối đến máy chủ API.', 'error');
    }
  };

  const testCamera = async (id: number) => {
    try {
      const res = await fetch(`${apiUrlFn(`/api/cameras/${id}/test`)}`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        showToast(`Kiểm tra kết nối: ${data.status}`, 'success');
        loadCameras();
      } else {
        showToast('Lỗi khi kiểm tra kết nối camera.', 'error');
      }
    } catch {
      showToast('Không thể kết nối đến máy chủ API.', 'error');
    }
  };

  const stopCameraStream = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) videoRef.current.srcObject = null;
  };

  const startWebcam = async () => {
    try {
      stopCameraStream();
      if (videoRef.current) {
        videoRef.current.removeAttribute('src');
        videoRef.current.load();
      }
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: CAPTURE_WIDTH, height: CAPTURE_HEIGHT, frameRate: 30, facingMode: 'user' },
        audio: false,
      });
      streamRef.current = stream;
      const video = videoRef.current;
      if (!video) {
        stream.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
        throw new Error('Video element is not ready');
      }
      video.srcObject = stream;
      video.muted = true;
      video.play().catch(() => {});
      setSourceType('webcam');
      addLog('Đã kết nối webcam.', 'system');
    } catch (err) {
      stopCameraStream();
      setSourceType('none');
      showToast(`Không thể truy cập webcam: ${err}`, 'error');
      console.error(err);
    }
  };

  const stopWebcam = () => {
    stopPipeline();
    stopCameraStream();
    setSourceType('none');
    setActiveTracksCount(0);
    setFps(0);
    setResponseLatencyMs(0);
    clearOverlayCanvas();
    addLog('Đã tắt webcam.', 'system');
  };

  const handleVideoUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      stopCameraStream();
      const url = URL.createObjectURL(file);
      if (videoRef.current) {
        videoRef.current.src = url;
        videoRef.current.loop = true;
        videoRef.current.play().catch(() => {});
      }
      setSourceType('video');
      addLog(`Đã tải video: ${file.name}`, 'system');
    }
  };

  const addLog = (text: string, type: 'entry' | 'exit' | 'system') => {
    const item: LogItem = { id: crypto.randomUUID(), time: new Date().toLocaleTimeString('vi-VN'), text, type };
    setLogs((prev) => [item, ...prev].slice(0, 50));
  };

  const resetStats = () => {
    setEntriesCount(0);
    setExitsCount(0);
    setLogs([]);
    addLog('Đã xóa thống kê và nhật ký.', 'system');
  };

  const togglePipeline = () => {
    if (isRunningRef.current) stopPipeline();
    else startPipeline();
  };

  const startPipeline = () => {
    if (sourceType === 'none') {
      showToast('Hãy kết nối webcam hoặc tải video trước.', 'error');
      return;
    }
    isRunningRef.current = true;
    frameSequenceRef.current += 1;
    processedFramesRef.current = 0;
    setIsRunning(true);
    setFps(0);
    setResponseLatencyMs(0);
    lastFrameTimeRef.current = performance.now();
    sessionTrackerIdRef.current = `session_${Math.floor(Date.now() / 1000)}`;
    addLog(`Bắt đầu phân tích (phiên ${sessionTrackerIdRef.current})`, 'system');
    scheduleNextFrame();
  };

  const stopPipeline = () => {
    if (!isRunningRef.current && loopTimeoutRef.current === null) return;
    const wasRunning = isRunningRef.current;
    isRunningRef.current = false;
    frameSequenceRef.current += 1;
    setIsRunning(false);
    if (loopTimeoutRef.current !== null) {
      clearTimeout(loopTimeoutRef.current);
      loopTimeoutRef.current = null;
    }
    if (wasRunning) addLog('Đã dừng phân tích.', 'system');
  };

  const scheduleNextFrame = (delayMs = 0) => {
    if (loopTimeoutRef.current !== null) clearTimeout(loopTimeoutRef.current);
    loopTimeoutRef.current = window.setTimeout(async () => {
      if (!isRunningRef.current) return;
      const startedAt = performance.now();
      await processCurrentFrame();
      const elapsed = performance.now() - startedAt;
      if (isRunningRef.current) scheduleNextFrame(Math.max(0, TARGET_FRAME_INTERVAL_MS - elapsed));
    }, delayMs);
  };

  const processCurrentFrame = async () => {
    const frameSequence = frameSequenceRef.current;
    const sessionId = sessionTrackerIdRef.current;
    const video = videoRef.current;
    if (!video || video.ended) return;
    if (video.paused && !video.srcObject) return;

    const offscreenCanvas = document.createElement('canvas');
    offscreenCanvas.width = CAPTURE_WIDTH;
    offscreenCanvas.height = CAPTURE_HEIGHT;
    const ctx = offscreenCanvas.getContext('2d');
    if (!ctx) return;
    ctx.drawImage(video, 0, 0, CAPTURE_WIDTH, CAPTURE_HEIGHT);

    const blob = await new Promise<Blob | null>((resolve) => {
      offscreenCanvas.toBlob((b) => resolve(b), 'image/jpeg', JPEG_QUALITY);
    });
    if (!blob) return;

    const formData = new FormData();
    const frameIndex = processedFramesRef.current;
    const shouldProbeIdentity = frameIndex < INITIAL_IDENTITY_PROBE_FRAMES || frameIndex % IDENTITY_PROBE_INTERVAL_FRAMES === 0;
    const shouldDetect = frameIndex < INITIAL_DETECTION_FRAMES || frameIndex % DETECTION_INTERVAL_FRAMES === 0 || shouldProbeIdentity;
    processedFramesRef.current += 1;
    formData.append('file', blob, 'frame.jpg');
    formData.append('session_id', sessionId);
    formData.append('line_config', JSON.stringify(lineConfig));
    formData.append('fast_mode', 'true');
    formData.append('identity_probe', shouldProbeIdentity ? 'true' : 'false');
    formData.append('detect_frame', shouldDetect ? 'true' : 'false');
    formData.append('identity_ttl_seconds', String(IDENTITY_TTL_SECONDS));

    try {
      const requestStart = performance.now();
      const response = await fetch(`${apiUrlFn('/api/process-frame')}`, {
        method: 'POST',
        body: formData,
      });
      if (!response.ok) {
        let detail = `API server returned ${response.status}`;
        try {
          const errBody = await response.json();
          if (errBody?.detail || errBody?.error) detail = `${errBody.error || 'error'}: ${errBody.detail || response.status}`;
        } catch { /* ignore */ }
        throw new Error(detail);
      }
      const result = await response.json();
      if (!isRunningRef.current || frameSequence !== frameSequenceRef.current || sessionId !== sessionTrackerIdRef.current) return;
      const endTime = performance.now();
      const frameDelta = Math.max(1, endTime - lastFrameTimeRef.current);
      setFps(Math.round(1000 / frameDelta));
      setResponseLatencyMs(Math.round(result.processing_ms || (endTime - requestStart)));
      lastFrameTimeRef.current = endTime;
      const tracks: Track[] = result.tracks || [];
      const crossingEvents: CrossingEvent[] = result.crossing_events || [];
      setActiveTracksCount(tracks.length);
      drawOverlay(tracks);
      handleCrossingEvents(tracks, crossingEvents);
    } catch (err) {
      console.error('Frame processing failed:', err);
      addLog(`Lỗi xử lý frame: ${err instanceof Error ? err.message : String(err)}`, 'system');
    }
  };

  const drawLineGuide = (ctx: CanvasRenderingContext2D, canvas: HTMLCanvasElement, colors: ReturnType<typeof readThemeColors>) => {
    const [p1, p2] = lineConfig;
    const mirrorX = (x: number) => (sourceType === 'webcam' ? canvas.width - x : x);
    const x1 = mirrorX(p1[0]);
    const x2 = mirrorX(p2[0]);
    const centerX = (x1 + x2) / 2;
    const centerY = (p1[1] + p2[1]) / 2;
    ctx.save();
    let entryDx = -(p2[1] - p1[1]);
    let entryDy = p2[0] - p1[0];
    const len = Math.hypot(entryDx, entryDy) || 1;
    entryDx /= len;
    entryDy /= len;
    if (sourceType === 'webcam') entryDx *= -1;

    const drawDirectionalArrow = (label: string, dx: number, dy: number, color: string) => {
      const startX = centerX - dx * 18;
      const startY = centerY - dy * 18;
      const endX = centerX + dx * 48;
      const endY = centerY + dy * 48;
      const angle = Math.atan2(endY - startY, endX - startX);
      ctx.strokeStyle = color;
      ctx.fillStyle = color;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(startX, startY);
      ctx.lineTo(endX, endY);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(endX, endY);
      ctx.lineTo(endX - 10 * Math.cos(angle - Math.PI / 6), endY - 10 * Math.sin(angle - Math.PI / 6));
      ctx.lineTo(endX - 10 * Math.cos(angle + Math.PI / 6), endY - 10 * Math.sin(angle + Math.PI / 6));
      ctx.closePath();
      ctx.fill();
      ctx.font = '700 12px Outfit, sans-serif';
      ctx.fillText(label, endX + dx * 8 - 12, endY + dy * 8 + 4);
    };
    drawDirectionalArrow('Vào', entryDx, entryDy, colors.entry);
    drawDirectionalArrow('Ra', -entryDx, -entryDy, colors.exit);
    ctx.restore();
  };

  const drawOverlay = (tracks: Track[]) => {
    const canvas = overlayCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const colors = readThemeColors();
    const mirrorX = (x: number) => (sourceType === 'webcam' ? canvas.width - x : x);
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (showLine) {
      const [p1, p2] = lineConfig;
      const x1 = mirrorX(p1[0]);
      const x2 = mirrorX(p2[0]);
      ctx.beginPath();
      ctx.moveTo(x1, p1[1]);
      ctx.lineTo(x2, p2[1]);
      ctx.lineWidth = 3;
      ctx.strokeStyle = colors.accent;
      ctx.stroke();
      ctx.fillStyle = colors.accent;
      ctx.beginPath();
      ctx.arc(x1, p1[1], 5, 0, Math.PI * 2);
      ctx.arc(x2, p2[1], 5, 0, Math.PI * 2);
      ctx.fill();
      ctx.font = '600 11px Outfit, sans-serif';
      ctx.fillStyle = colors.accent;
      ctx.fillText('Hướng vào', (x1 + x2) / 2 - 28, (p1[1] + p2[1]) / 2 - 10);
    }
    if (showLine) drawLineGuide(ctx, canvas, colors);

    if (showBboxes) {
      tracks.forEach((track) => {
        const [bx1, by1, bx2, by2] = track.bbox;
        const x1 = Math.min(mirrorX(bx1), mirrorX(bx2));
        const x2 = Math.max(mirrorX(bx1), mirrorX(bx2));
        const width = x2 - x1;
        const height = by2 - by1;
        const isKnown = track.identity_type === 'KNOWN';
        const color = isKnown ? colors.entry : colors.exit;
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.setLineDash(track.predicted ? [8, 5] : []);
        ctx.strokeRect(x1, by1, width, height);
        ctx.setLineDash([]);
        ctx.fillStyle = isKnown ? colors.entryFill : colors.exitFill;
        ctx.fillRect(x1, by1, width, height);
        if (showTrackIds) {
          const name = isKnown ? track.person_name : 'Khách';
          const label = `#${track.track_id} ${name}`;
          ctx.font = '600 11px JetBrains Mono, monospace';
          const textWidth = ctx.measureText(label).width;
          ctx.fillStyle = color;
          ctx.fillRect(x1, by1 - 20, textWidth + 10, 20);
          ctx.fillStyle = colors.labelFg;
          ctx.fillText(label, x1 + 4, by1 - 5);
        }
      });
    }
  };

  const triggerCounterPulse = (direction: 'entry' | 'exit') => {
    if (direction === 'entry') {
      setAnimateEntry(true);
      setVideoFlash('entry');
      window.setTimeout(() => setAnimateEntry(false), 300);
    } else {
      setAnimateExit(true);
      setVideoFlash('exit');
      window.setTimeout(() => setAnimateExit(false), 300);
    }
    window.setTimeout(() => setVideoFlash(null), 400);
  };

  const handleCrossingEvents = (tracks: Track[], events: CrossingEvent[]) => {
    events.forEach((event) => {
      const track = tracks.find((t) => t.track_id === event.track_id);
      if (event.person_name && track) {
        track.person_name = event.person_name;
        track.identity_type = event.identity_type || track.identity_type;
      }
      const name = track?.person_name || 'Khách';
      const type = event.identity_type || track?.identity_type || 'UNKNOWN';
      const typeLabel = type === 'KNOWN' ? 'đã biết' : type === 'UNRESOLVED' ? 'chưa xác định' : 'khách';
      if (event.direction === 'ENTRY') {
        setEntriesCount((prev) => prev + 1);
        triggerCounterPulse('entry');
        addLog(`Vào: ${name} (${typeLabel}) #${event.track_id}`, 'entry');
      } else if (event.direction === 'EXIT') {
        setExitsCount((prev) => prev + 1);
        triggerCounterPulse('exit');
        addLog(`Ra: ${name} (${typeLabel}) #${event.track_id}`, 'exit');
      }
    });
  };

  const clearOverlayCanvas = () => {
    const canvas = overlayCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const colors = readThemeColors();
    const mirrorX = (x: number) => (sourceType === 'webcam' ? canvas.width - x : x);
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    if (sourceType !== 'none' && showLine) {
      const [p1, p2] = lineConfig;
      const x1 = mirrorX(p1[0]);
      const x2 = mirrorX(p2[0]);
      ctx.beginPath();
      ctx.moveTo(x1, p1[1]);
      ctx.lineTo(x2, p2[1]);
      ctx.lineWidth = 3;
      ctx.strokeStyle = colors.accent;
      ctx.stroke();
      ctx.fillStyle = colors.accent;
      ctx.beginPath();
      ctx.arc(x1, p1[1], 5, 0, Math.PI * 2);
      ctx.arc(x2, p2[1], 5, 0, Math.PI * 2);
      ctx.fill();
      drawLineGuide(ctx, canvas, colors);
    }
  };

  const getMouseCoords = (e: React.MouseEvent<HTMLCanvasElement>): [number, number] => {
    const canvas = overlayCanvasRef.current;
    if (!canvas) return [0, 0];
    const rect = canvas.getBoundingClientRect();
    let x = Math.round(((e.clientX - rect.left) / rect.width) * canvas.width);
    const y = Math.round(((e.clientY - rect.top) / rect.height) * canvas.height);
    if (sourceType === 'webcam') x = canvas.width - x;
    return [x, y];
  };

  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!showLine || isRunning) return;
    const coords = getMouseCoords(e);
    setIsDrawing(true);
    setLineConfig([coords, coords]);
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isDrawing) return;
    const coords = getMouseCoords(e);
    setLineConfig((prev) => [prev[0], coords]);
  };

  const handleMouseUp = () => {
    if (!isDrawing) return;
    setIsDrawing(false);
    addLog(`Đã cấu hình vạch ảo: (${lineConfig[0].join(',')}) - (${lineConfig[1].join(',')})`, 'system');
  };

  const screenClass = [
    'screen-container',
    sourceType === 'none' ? 'is-empty' : '',
    isRunning ? 'is-live' : '',
    videoFlash === 'entry' ? 'flash-entry' : '',
    videoFlash === 'exit' ? 'flash-exit' : '',
  ].filter(Boolean).join(' ');

  const filteredLogs = logFilter === 'all' ? logs : logs.filter((l) => l.type === logFilter);

  return (
    <div className="dashboard-grid page-view">
      <section className="panel">
        <h2 className="panel-title"><SlidersHorizontal {...ICON} /> Điều khiển</h2>
        <div className="control-group">
          <span className="control-label">Nguồn camera</span>
          <div className="segmented-control">
            <button type="button" className={`segmented-btn ${cameraSourceTab === 'webcam' ? 'active' : ''}`} onClick={() => setCameraSourceTab('webcam')}>Webcam</button>
            <button type="button" className={`segmented-btn ${cameraSourceTab === 'upload' ? 'active' : ''}`} onClick={() => setCameraSourceTab('upload')}>Tải video</button>
            <button type="button" className={`segmented-btn ${cameraSourceTab === 'rtsp' ? 'active' : ''}`} onClick={() => setCameraSourceTab('rtsp')}>RTSP</button>
          </div>
          {cameraSourceTab === 'webcam' && (
            <div className="tab-content tab-content--centered webcam-state">
              {sourceType === 'webcam' ? (
                <>
                  <div className="tab-illustration tab-illustration--active">
                    <Camera size={36} weight="duotone" />
                  </div>
                  <p className="tab-desc"><strong>Webcam đang bật.</strong></p>
                  <button type="button" className="btn btn-block btn-danger" onClick={stopWebcam}>
                    <Camera {...ICON} /> Tắt webcam
                  </button>
                </>
              ) : (
                <>
                  <div className="tab-illustration">
                    <Camera size={36} weight="light" />
                  </div>
                  <p className="tab-desc">Sử dụng webcam tích hợp hoặc webcam USB để theo dõi trực tiếp.</p>
                  <button type="button" className="btn btn-block" onClick={startWebcam} disabled={isRunning}>
                    <Camera {...ICON} /> Bật webcam
                  </button>
                </>
              )}
            </div>
          )}
          {cameraSourceTab === 'upload' && (
            <div className="tab-content tab-content--centered">
              <div className="file-dropzone">
                <input type="file" id="file-upload" accept="video/*" hidden onChange={handleVideoUpload} disabled={isRunning} />
                <label htmlFor="file-upload" className={`file-dropzone-label ${isRunning ? 'is-disabled' : ''}`}>
                  <UploadSimple size={32} weight="light" />
                  <div className="file-dropzone-title">Tải video mẫu</div>
                  <div className="file-dropzone-hint">MP4, WebM, AVI · Tối đa 10MB</div>
                </label>
              </div>
            </div>
          )}
          {cameraSourceTab === 'rtsp' && (
            <div className="tab-content">
              <input type="text" className="text-input" placeholder="Tên camera (vd: Cổng chính)" value={newCamName} onChange={(e) => setNewCamName(e.target.value)} disabled={isRunning} />
              <input type="text" className="text-input" placeholder="URL (vd: rtsp://...)" value={newCamUrl} onChange={(e) => setNewCamUrl(e.target.value)} disabled={isRunning} />
              <button type="button" className="btn btn-block btn-sm" onClick={handleAddCamera} disabled={isRunning}>
                <Plus {...ICON_SM} /> Thêm camera
              </button>
              {camerasList.length > 0 && (
                <div className="camera-list">
                  {camerasList.map((cam) => (
                    editingCamId === cam.id ? (
                      <div key={cam.id} className="camera-item camera-item--editing">
                        <input type="text" className="text-input text-input--sm" value={editCamName} onChange={(e) => setEditCamName(e.target.value)} placeholder="Tên camera" />
                        <input type="text" className="text-input text-input--sm" value={editCamUrl} onChange={(e) => setEditCamUrl(e.target.value)} placeholder="URL RTSP" />
                        <div className="camera-item-actions">
                          <button type="button" className="btn btn-sm btn-primary" onClick={handleUpdateCamera}>Lưu</button>
                          <button type="button" className="btn btn-sm btn-ghost" onClick={cancelEdit}>Huỷ</button>
                        </div>
                      </div>
                    ) : (
                      <div key={cam.id} className="camera-item">
                        <div className="camera-item-head">
                          <VideoCamera size={14} weight="fill" />
                          <span className="camera-item-name">{cam.name}</span>
                          <span className={`badge ${cam.status === 'ONLINE' ? 'success' : 'danger'}`}>{cam.status}</span>
                        </div>
                        <div className="camera-item-url">{cam.source_url}</div>
                        <div className="camera-item-actions">
                          <button type="button" className="btn-ghost btn-sm" onClick={() => testCamera(cam.id)}>Kiểm tra</button>
                          <button type="button" className="btn-ghost btn-sm" onClick={() => startEdit(cam)} title="Sửa camera">
                            <Pencil size={14} />
                          </button>
                          <button type="button" className="btn-ghost btn-sm camera-item-delete" onClick={() => handleRemoveCamera(cam.id, cam.name)} title="Xoá camera">
                            <X size={14} weight="bold" />
                          </button>
                        </div>
                      </div>
                    )
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
        <div className="control-group control-group-divider">
          <span className="control-label">Lớp hiển thị</span>
          <div className="switch-label">
            <span>Khung người</span>
            <label className="switch"><input type="checkbox" checked={showBboxes} onChange={(e) => setShowBboxes(e.target.checked)} /><span className="slider" /></label>
          </div>
          <div className="switch-label">
            <span>Mã theo dõi</span>
            <label className="switch"><input type="checkbox" checked={showTrackIds} onChange={(e) => setShowTrackIds(e.target.checked)} /><span className="slider" /></label>
          </div>
          <div className="switch-label">
            <span>Vạch ảo</span>
            <label className="switch"><input type="checkbox" checked={showLine} onChange={(e) => setShowLine(e.target.checked)} /><span className="slider" /></label>
          </div>
        </div>
        <div className="panel-actions">
          <button type="button" className={`btn btn-block ${isRunning ? 'btn-danger' : ''}`} onClick={togglePipeline}>
            {isRunning ? <><Stop {...ICON} weight="fill" /> Dừng phân tích</> : <><Play {...ICON} weight="fill" /> Bắt đầu phân tích</>}
          </button>
          <button type="button" className="btn btn-danger btn-block" onClick={resetStats}>
            <Trash {...ICON} /> Xóa thống kê
          </button>
        </div>
      </section>

      <section className="panel video-panel">
        <h2 className="panel-title"><VideoCamera {...ICON} /> Khung hình trực tiếp</h2>
        <div className={screenClass} data-testid="video-screen">
          <span className="screen-hud screen-hud--tl" aria-hidden="true" />
          <span className="screen-hud screen-hud--tr" aria-hidden="true" />
          <span className="screen-hud screen-hud--bl" aria-hidden="true" />
          <span className="screen-hud screen-hud--br" aria-hidden="true" />
          <span className="screen-scanline" aria-hidden="true" />
          <video ref={videoRef} className={`video-element ${sourceType === 'none' ? 'media-hidden' : ''} ${sourceType === 'webcam' ? 'is-mirrored' : ''}`} playsInline muted autoPlay />
          <canvas ref={overlayCanvasRef} className={`canvas-overlay ${sourceType === 'none' ? 'media-hidden' : ''}`} width={640} height={480} onMouseDown={handleMouseDown} onMouseMove={handleMouseMove} onMouseUp={handleMouseUp} />
          {sourceType !== 'none' && (
            <div className="video-counters">
              <div className="video-counter entry">
                <div className="video-counter-label"><ArrowLineDownLeft size={12} weight="bold" /> Lượt vào</div>
                <div className={`video-counter-value ${animateEntry ? 'bump' : ''}`}>{entriesCount}</div>
              </div>
              <div className="video-counter exit">
                <div className="video-counter-label"><ArrowLineUpRight size={12} weight="bold" /> Lượt ra</div>
                <div className={`video-counter-value ${animateExit ? 'bump' : ''}`}>{exitsCount}</div>
              </div>
            </div>
          )}
          {sourceType === 'none' && (
            <div className="screen-placeholder">
              <div className="placeholder-radar" aria-hidden="true"><span /><span /><span /></div>
              <VideoCamera size={48} weight="duotone" />
              <div className="screen-placeholder-title">Chưa có nguồn video</div>
              <div className="screen-placeholder-hint">Bật webcam hoặc tải video ở panel bên trái.</div>
            </div>
          )}
        </div>
        {sourceType !== 'none' && (
          <div className="video-counters video-counters--dock">
            <div className="video-counter entry">
              <div className="video-counter-label"><ArrowLineDownLeft size={12} weight="bold" /> Lượt vào</div>
              <div className={`video-counter-value ${animateEntry ? 'bump' : ''}`}>{entriesCount}</div>
            </div>
            <div className="video-counter exit">
              <div className="video-counter-label"><ArrowLineUpRight size={12} weight="bold" /> Lượt ra</div>
              <div className={`video-counter-value ${animateExit ? 'bump' : ''}`}>{exitsCount}</div>
            </div>
          </div>
        )}
        <div className="video-meta">
          <span>Đang theo dõi: <strong>{activeTracksCount}</strong></span>
          <span>Tốc độ xử lý: <strong>{isRunning ? `${fps} FPS` : '0 FPS'}</strong></span>
          <span>Latency: <strong>{isRunning ? `${responseLatencyMs} ms` : '0 ms'}</strong></span>
          {!isRunning && sourceType !== 'none' && showLine && (
            <span className="video-meta-hint">Kéo chuột trên khung hình để vẽ vạch ảo</span>
          )}
        </div>
      </section>

      <section className="panel">
        <h2 className="panel-title"><FileText {...ICON} /> Nhật ký hoạt động</h2>
        <div className="log-filters">
          {(['all', 'entry', 'exit', 'system'] as LogFilter[]).map((f) => (
            <button key={f} type="button" className={`log-filter-btn ${logFilter === f ? 'active' : ''}`} onClick={() => setLogFilter(f)}>
              {f === 'all' ? 'Tất cả' : f === 'entry' ? 'Vào' : f === 'exit' ? 'Ra' : 'Hệ thống'}
            </button>
          ))}
        </div>
        <div className="log-container">
          {filteredLogs.length === 0 ? (
            <div className="log-empty">Chưa có sự kiện. Bắt đầu phân tích để theo dõi ra/vào.</div>
          ) : (
            filteredLogs.map((item) => (
              <div key={item.id} className={`log-entry ${item.type}`}>
                <span className="log-time">{item.time}</span>
                <span className="log-text">{item.text}</span>
              </div>
            ))
          )}
        </div>
      </section>
    </div>
  );
}
