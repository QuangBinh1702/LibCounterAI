import React, { useState, useEffect, useRef } from 'react';
import {
  VideoCamera,
  Users,
  CalendarBlank,
  ChartBar,
  GearSix,
  Camera,
  UploadSimple,
  Play,
  Stop,
  Trash,
  ArrowLineDownLeft,
  ArrowLineUpRight,
  FileText,
  UserPlus,
  Plus,
  Plugs,
  Pencil,
  X,
} from '@phosphor-icons/react';
import { AnimatePresence } from 'framer-motion';
import { ToastContainer } from './components/Toast';
import { ThemeToggle } from './components/ThemeToggle';
import { NavTabs } from './components/NavTabs';
import { PageTransition } from './components/PageTransition';
import { SkeletonRows } from './components/Skeleton';
import { PeriodFilter } from './components/PeriodFilter';
import { ExportMenu, type ExportFormat } from './components/ExportMenu';
import { TrafficChart } from './components/TrafficChart';
import { useToast } from './hooks/useToast';
import { readThemeColors, useTheme } from './hooks/useTheme';
import {
  formatRangeLabel,
  periodQuery,
  periodShortLabel,
  rangeForPreset,
  type PeriodPreset,
} from './utils/dateRange';
import {
  exportSessionsCsv,
  exportSessionsExcel,
  exportSessionsPdf,
} from './utils/exportSessions';

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

interface Person {
  id: number;
  full_name: string;
  member_code: string;
  role: string;
  status: string;
}

interface VisitSession {
  id: number;
  person_name: string;
  member_code: string | null;
  entry_at: string | null;
  exit_at: string | null;
  duration_seconds: number | null;
  status: string;
}

interface OccupancyStats {
  current_occupancy: number;
  total_entries_today: number;
  total_exits_today: number;
  known_visitors_today: number;
  unknown_visitors_today: number;
  total_sessions_today: number;
}

interface HourlyStat {
  hour: number;
  entry: number;
  exit: number;
}

type CameraSourceTab = 'webcam' | 'upload' | 'rtsp';
type LogFilter = 'all' | 'entry' | 'exit' | 'system';

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

const NAV_TABS = [
  { id: 'monitor' as const, label: 'Giám sát', Icon: VideoCamera },
  { id: 'registry' as const, label: 'Thành viên', Icon: Users },
  { id: 'history' as const, label: 'Lịch sử', Icon: CalendarBlank },
  { id: 'analytics' as const, label: 'Thống kê', Icon: ChartBar },
];

const ROLE_LABELS: Record<string, string> = {
  STUDENT: 'Sinh viên',
  FACULTY: 'Giảng viên',
  STAFF: 'Nhân viên',
  GUEST: 'Khách',
};

function App() {
  const { toasts, show: showToast, dismiss: dismissToast } = useToast();
  const { theme, toggleTheme } = useTheme();

  const [activeTab, setActiveTab] = useState<'monitor' | 'registry' | 'history' | 'analytics'>('monitor');
  const [cameraSourceTab, setCameraSourceTab] = useState<CameraSourceTab>('webcam');
  const [logFilter, setLogFilter] = useState<LogFilter>('all');

  const [backendUrl, setBackendUrl] = useState('http://localhost:8000');

  const apiUrl = (path: string) => {
    const base = backendUrl.trim().replace(/\/$/, '');
    const suffix = path.startsWith('/') ? path : `/${path}`;
    return `${base}${suffix}`;
  };
  const [isBackendOnline, setIsBackendOnline] = useState(false);
  const [sourceType, setSourceType] = useState<'webcam' | 'video' | 'none'>('none');
  const [isRunning, setIsRunning] = useState(false);
  const [fps, setFps] = useState(0);
  const [responseLatencyMs, setResponseLatencyMs] = useState(0);
  const [activeTracksCount, setActiveTracksCount] = useState(0);

  const [entriesCount, setEntriesCount] = useState(0);
  const [exitsCount, setExitsCount] = useState(0);
  const [logs, setLogs] = useState<LogItem[]>([]);

  const [showBboxes, setShowBboxes] = useState(true);
  const [showLine, setShowLine] = useState(true);
  const [showTrackIds, setShowTrackIds] = useState(true);

  const [lineConfig, setLineConfig] = useState<[[number, number], [number, number]]>([
    [320, 0],
    [320, 480],
  ]);
  const [isDrawing, setIsDrawing] = useState(false);

  const [animateEntry, setAnimateEntry] = useState(false);
  const [animateExit, setAnimateExit] = useState(false);
  const [videoFlash, setVideoFlash] = useState<'entry' | 'exit' | null>(null);

  const [persons, setPersons] = useState<Person[]>([]);
  const [regName, setRegName] = useState('');
  const [regCode, setRegCode] = useState('');
  const [regRole, setRegRole] = useState('STUDENT');
  const [regStatus, setRegStatus] = useState('ACTIVE');
  const [regPhoto, setRegPhoto] = useState<File | null>(null);
  const [editingPerson, setEditingPerson] = useState<Person | null>(null);
  const [editName, setEditName] = useState('');
  const [editCode, setEditCode] = useState('');
  const [editRole, setEditRole] = useState('STUDENT');
  const [editStatus, setEditStatus] = useState('ACTIVE');
  const [editPhoto, setEditPhoto] = useState<File | null>(null);

  const startEditPerson = (person: Person) => {
    setEditingPerson(person);
    setEditName(person.full_name);
    setEditCode(person.member_code);
    setEditRole(person.role);
    setEditStatus(person.status);
    setEditPhoto(null);
  };

  const cancelEditPerson = () => {
    setEditingPerson(null);
    setEditName('');
    setEditCode('');
    setEditRole('STUDENT');
    setEditStatus('ACTIVE');
    setEditPhoto(null);
  };

  const [sessions, setSessions] = useState<VisitSession[]>([]);
  const initialRange = rangeForPreset('day');
  const [periodPreset, setPeriodPreset] = useState<PeriodPreset>('day');
  const [rangeFrom, setRangeFrom] = useState(initialRange.from);
  const [rangeTo, setRangeTo] = useState(initialRange.to);
  const [draftFrom, setDraftFrom] = useState(initialRange.from);
  const [draftTo, setDraftTo] = useState(initialRange.to);

  const [occupancy, setOccupancy] = useState<OccupancyStats>({
    current_occupancy: 0,
    total_entries_today: 0,
    total_exits_today: 0,
    known_visitors_today: 0,
    unknown_visitors_today: 0,
    total_sessions_today: 0,
  });
  const [hourlyStats, setHourlyStats] = useState<HourlyStat[]>([]);

  const [camerasList, setCamerasList] = useState<{ id: number; name: string; source_url: string; status: string }[]>([]);
  const [newCamName, setNewCamName] = useState('');
  const [newCamUrl, setNewCamUrl] = useState('');

  const [loadingRegistry, setLoadingRegistry] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [loadingAnalytics, setLoadingAnalytics] = useState(false);

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const overlayCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const loopTimeoutRef = useRef<number | null>(null);
  const sessionTrackerIdRef = useRef<string>(`session_${Math.floor(Date.now() / 1000)}`);
  const streamRef = useRef<MediaStream | null>(null);
  const lastFrameTimeRef = useRef<number>(0);
  const isRunningRef = useRef(false);
  const frameSequenceRef = useRef(0);
  const processedFramesRef = useRef(0);

  useEffect(() => {
    let active = true;
    const checkHealth = async () => {
      try {
        const res = await fetch(`${apiUrl('/api/health')}`);
        if (active) setIsBackendOnline(res.ok);
      } catch {
        if (active) setIsBackendOnline(false);
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 5000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [backendUrl]);

  useEffect(() => {
    // Overlay only — do not tear down the live stream when sourceType flips to webcam/video.
    // startWebcam / handleVideoUpload / stopWebcam own stream lifecycle.
    stopPipeline();
    clearOverlayCanvas();
  }, [sourceType]);

  useEffect(() => {
    if (activeTab === 'monitor') {
      loadCameras();
    } else if (activeTab === 'registry') {
      loadPersons();
    } else if (activeTab === 'history') {
      loadFilteredSessions();
    } else if (activeTab === 'analytics') {
      loadAnalytics();
    }
  }, [activeTab, backendUrl, rangeFrom, rangeTo]);

  useEffect(() => {
    loadCameras();
  }, [backendUrl]);

  useEffect(() => {
    clearOverlayCanvas();
  }, [lineConfig, sourceType, showLine, theme]);

  const loadCameras = async () => {
    try {
      const res = await fetch(`${apiUrl('/api/cameras')}`);
      if (res.ok) setCamerasList(await res.json());
    } catch (err) {
      console.error('Failed to load cameras:', err);
    }
  };

  const handleAddCamera = async () => {
    if (!newCamName || !newCamUrl) {
      showToast('Vui lòng nhập tên camera và địa chỉ kết nối.', 'error');
      return;
    }
    try {
      const res = await fetch(`${apiUrl('/api/cameras')}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newCamName,
          source_type: 'RTSP',
          source_url: newCamUrl,
        }),
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

  const testCamera = async (id: number) => {
    try {
      const res = await fetch(`${apiUrl(`/api/cameras/${id}/test`)}`, { method: 'POST' });
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

  const loadPersons = async () => {
    setLoadingRegistry(true);
    try {
      const res = await fetch(`${apiUrl('/api/persons')}`);
      if (res.ok) setPersons(await res.json());
    } catch (err) {
      console.error('Failed to load persons:', err);
      showToast('Không tải được danh sách thành viên.', 'error');
    } finally {
      setLoadingRegistry(false);
    }
  };

  const parseSessionResponse = (data: unknown): VisitSession[] => {
    if (Array.isArray(data)) return data;
    if (data && typeof data === 'object' && 'items' in data && Array.isArray((data as { items: VisitSession[] }).items)) {
      return (data as { items: VisitSession[] }).items;
    }
    return [];
  };

  const reportQuery = () => periodQuery({ from: rangeFrom, to: rangeTo });
  const activeRangeLabel = formatRangeLabel({ from: rangeFrom, to: rangeTo }, periodPreset);

  const applyPeriodPreset = (preset: PeriodPreset) => {
    const next = rangeForPreset(preset);
    setPeriodPreset(preset);
    setDraftFrom(next.from);
    setDraftTo(next.to);
    setRangeFrom(next.from);
    setRangeTo(next.to);
  };

  const applyCustomRange = () => {
    if (!draftFrom || !draftTo) {
      showToast('Vui lòng chọn đầy đủ ngày bắt đầu và kết thúc.', 'error');
      return;
    }
    if (draftFrom > draftTo) {
      showToast('Ngày bắt đầu phải trước hoặc bằng ngày kết thúc.', 'error');
      return;
    }
    setPeriodPreset(draftFrom === draftTo ? 'day' : 'week');
    setRangeFrom(draftFrom);
    setRangeTo(draftTo);
  };

  const loadFilteredSessions = async () => {
    setLoadingHistory(true);
    try {
      const res = await fetch(`${apiUrl(`/api/sessions?${reportQuery()}`)}`);
      if (res.ok) setSessions(parseSessionResponse(await res.json()));
      else showToast('Không lọc được dữ liệu theo khoảng đã chọn.', 'error');
    } catch (err) {
      console.error('Failed to load filtered sessions:', err);
      showToast('Không tải được lịch sử phiên.', 'error');
    } finally {
      setLoadingHistory(false);
    }
  };

  const loadAnalytics = async () => {
    setLoadingAnalytics(true);
    try {
      const q = reportQuery();
      const resOcc = await fetch(`${apiUrl(`/api/stats/occupancy?${q}`)}`);
      const resHourly = await fetch(`${apiUrl(`/api/stats/hourly?${q}`)}`);
      if (resOcc.ok && resHourly.ok) {
        setOccupancy(await resOcc.json());
        const hourly = await resHourly.json();
        const byHour = new Map<number, HourlyStat>(
          (Array.isArray(hourly) ? hourly : []).map((s: HourlyStat) => [s.hour, s]),
        );
        setHourlyStats(
          Array.from({ length: 24 }, (_, hour) => byHour.get(hour) ?? { hour, entry: 0, exit: 0 }),
        );
      } else {
        showToast('Không tải được dữ liệu thống kê.', 'error');
      }
    } catch (err) {
      console.error('Failed to load analytics:', err);
      showToast('Không tải được dữ liệu thống kê.', 'error');
    } finally {
      setLoadingAnalytics(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!regName || !regCode || !regRole || !regPhoto) {
      showToast('Vui lòng điền đầy đủ thông tin và chọn ảnh chân dung.', 'error');
      return;
    }
    const formData = new FormData();
    formData.append('full_name', regName);
    formData.append('member_code', regCode);
    formData.append('role', regRole);
    formData.append('status', regStatus);
    formData.append('file', regPhoto);

    try {
      const res = await fetch(`${apiUrl('/api/persons/register')}`, {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) {
        const err = await res.json();
        showToast(`Đăng ký thất bại: ${err.detail || 'Lỗi không xác định'}`, 'error');
        return;
      }
      showToast('Đăng ký thành viên mới thành công.', 'success');
      setRegName('');
      setRegCode('');
      setRegRole('STUDENT');
      setRegStatus('ACTIVE');
      setRegPhoto(null);
      loadPersons();
    } catch (err) {
      showToast(`Lỗi kết nối backend: ${err}`, 'error');
    }
  };

  const handleUpdatePerson = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingPerson || !editName || !editCode || !editRole) {
      showToast('Vui lòng điền đầy đủ thông tin.', 'error');
      return;
    }
    const formData = new FormData();
    formData.append('full_name', editName);
    formData.append('member_code', editCode);
    formData.append('role', editRole);
    formData.append('status', editStatus);
    if (editPhoto) {
      formData.append('file', editPhoto);
    }

    try {
      const res = await fetch(`${apiUrl(`/api/persons/${editingPerson.id}`)}`, {
        method: 'PUT',
        body: formData,
      });
      if (!res.ok) {
        const err = await res.json();
        showToast(`Cập nhật thất bại: ${err.detail || 'Lỗi không xác định'}`, 'error');
        return;
      }
      showToast('Cập nhật thành viên thành công.', 'success');
      setEditingPerson(null);
      loadPersons();
    } catch (err) {
      showToast(`Lỗi kết nối backend: ${err}`, 'error');
    }
  };

  const handleDeletePerson = async (id: number) => {
    if (!window.confirm('Bạn có chắc muốn xóa thành viên này? Dữ liệu sinh trắc học sẽ bị xóa hoàn toàn.')) return;
    try {
      const res = await fetch(`${apiUrl(`/api/persons/${id}`)}`, { method: 'DELETE' });
      if (res.ok) {
        showToast('Đã xóa thành viên.', 'success');
        loadPersons();
      } else {
        showToast('Xóa thành viên thất bại.', 'error');
      }
    } catch (err) {
      showToast(`Lỗi kết nối: ${err}`, 'error');
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
      await video.play();
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
        videoRef.current.play();
      }
      setSourceType('video');
      addLog(`Đã tải video: ${file.name}`, 'system');
    }
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
    // Webcam/MediaStream can briefly report paused while still producing frames.
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
    const shouldDetect =
      frameIndex < INITIAL_DETECTION_FRAMES ||
      frameIndex % DETECTION_INTERVAL_FRAMES === 0 ||
      shouldProbeIdentity;
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
        const response = await fetch(`${apiUrl('/api/process-frame')}`, {
          method: 'POST',
          body: formData,
        });
        if (!response.ok) {
          let detail = `API server returned ${response.status}`;
          try {
            const errBody = await response.json();
            if (errBody?.detail || errBody?.error) {
              detail = `${errBody.error || 'error'}: ${errBody.detail || response.status}`;
            }
          } catch {
            // ignore JSON parse errors
          }
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

  const drawLineGuide = (
    ctx: CanvasRenderingContext2D,
    canvas: HTMLCanvasElement,
    colors: ReturnType<typeof readThemeColors>,
  ) => {
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

    if (showLine) {
      drawLineGuide(ctx, canvas, colors);
    }

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
      const typeLabel =
        type === 'KNOWN' ? 'đã biết' :
        type === 'UNRESOLVED' ? 'chưa xác định' :
        'khách';

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
    // Webcam preview is mirrored in CSS; store line points in raw (unmirrored) frame space.
    if (sourceType === 'webcam') {
      x = canvas.width - x;
    }
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

  const addLog = (text: string, type: 'entry' | 'exit' | 'system') => {
    const item: LogItem = {
      id: crypto.randomUUID(),
      time: new Date().toLocaleTimeString('vi-VN'),
      text,
      type,
    };
    setLogs((prev) => [item, ...prev].slice(0, 50));
  };

  const resetStats = () => {
    setEntriesCount(0);
    setExitsCount(0);
    setLogs([]);
    addLog('Đã xóa thống kê và nhật ký.', 'system');
  };

  const handleExport = async (format: ExportFormat) => {
    try {
      let rows = sessions;
      const res = await fetch(`${apiUrl(`/api/sessions?${reportQuery()}`)}`);
      if (res.ok) {
        rows = parseSessionResponse(await res.json());
        setSessions(rows);
      }
      if (rows.length === 0) {
        showToast('Không có dữ liệu phiên trong khoảng đã lọc để xuất.', 'error');
        return;
      }
      if (format === 'csv') exportSessionsCsv(rows, rangeFrom, rangeTo);
      else if (format === 'excel') exportSessionsExcel(rows, rangeFrom, rangeTo);
      else exportSessionsPdf(rows, rangeFrom, rangeTo, activeRangeLabel);
      showToast(`Đã xuất báo cáo ${format.toUpperCase()} theo ${periodShortLabel(periodPreset)}.`, 'success');
    } catch (err) {
      console.error('Export failed:', err);
      showToast('Xuất file thất bại.', 'error');
    }
  };

  const filteredLogs = logFilter === 'all' ? logs : logs.filter((l) => l.type === logFilter);

  const screenClass = [
    'screen-container',
    isRunning ? 'is-live' : '',
    videoFlash === 'entry' ? 'flash-entry' : '',
    videoFlash === 'exit' ? 'flash-exit' : '',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <>
      <a className="skip-link" href="#main-content">
        Chuyển đến nội dung
      </a>
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />

      <header className="app-header">
        <div className="brand">
          <div className="brand-icon">L</div>
          <div className="brand-copy">
            <h1 className="brand-name">LibCounterAI</h1>
            <span className="brand-tagline">Giám sát thư viện thời gian thực</span>
          </div>
        </div>

        <NavTabs tabs={NAV_TABS} activeTab={activeTab} onChange={setActiveTab} iconProps={ICON_SM} />

        <div className="system-status">
          <ThemeToggle theme={theme} onToggle={toggleTheme} />
          <div className="status-indicator" data-testid="backend-status">
            <Plugs {...ICON_SM} />
            Máy chủ
            <span className={`dot ${isBackendOnline ? '' : 'offline'}`} />
            {isBackendOnline ? 'Trực tuyến' : 'Ngoại tuyến'}
          </div>
        </div>
      </header>

      <div className="page-transition-stage">
      <AnimatePresence mode="wait" initial={false}>
      {activeTab === 'monitor' && (
        <PageTransition key="monitor" className="dashboard-grid page-view" testId="view-monitor">
          <section className="panel">
            <h2 className="panel-title">
              <GearSix {...ICON} />
              Điều khiển
            </h2>

            <div className="control-group">
              <span className="control-label">Địa chỉ API</span>
                <input
                  type="text"
                  className="text-input"
                  value={backendUrl}
                  onChange={(e) => setBackendUrl(e.target.value)}
                  placeholder="http://localhost:8000"
                  disabled={isRunning}
                />
            </div>

            <div className="control-group">
              <span className="control-label">Nguồn camera</span>
              <div className="segmented-control">
                <button type="button" className={`segmented-btn ${cameraSourceTab === 'webcam' ? 'active' : ''}`} onClick={() => setCameraSourceTab('webcam')}>
                  Webcam
                </button>
                <button type="button" className={`segmented-btn ${cameraSourceTab === 'upload' ? 'active' : ''}`} onClick={() => setCameraSourceTab('upload')}>
                  Tải video
                </button>
                <button type="button" className={`segmented-btn ${cameraSourceTab === 'rtsp' ? 'active' : ''}`} onClick={() => setCameraSourceTab('rtsp')}>
                  RTSP
                </button>
              </div>

              {cameraSourceTab === 'webcam' && (
                sourceType === 'webcam' ? (
                  <button type="button" className="btn btn-block btn-danger" onClick={stopWebcam}>
                    <Camera {...ICON} />
                    Tắt webcam
                  </button>
                ) : (
                  <button type="button" className="btn btn-block" onClick={startWebcam} disabled={isRunning}>
                    <Camera {...ICON} />
                    Bật webcam
                  </button>
                )
              )}

              {cameraSourceTab === 'upload' && (
                <div className="file-dropzone">
                  <input
                    type="file"
                    id="file-upload"
                    accept="video/*"
                    hidden
                    onChange={handleVideoUpload}
                    disabled={isRunning}
                  />
                  <label
                    htmlFor="file-upload"
                    className={`file-dropzone-label ${isRunning ? 'is-disabled' : ''}`}
                  >
                    <UploadSimple size={28} weight="regular" />
                    <div className="file-dropzone-title">Tải video mẫu</div>
                    <div className="file-dropzone-hint">MP4, WebM, AVI · Tối đa 10MB</div>
                  </label>
                </div>
              )}

              {cameraSourceTab === 'rtsp' && (
                <>
                  <input
                    type="text"
                    className="text-input"
                    placeholder="Tên camera (vd: Cổng chính)"
                    value={newCamName}
                    onChange={(e) => setNewCamName(e.target.value)}
                    disabled={isRunning}
                  />
                  <input
                    type="text"
                    className="text-input"
                    placeholder="URL (vd: rtsp://...)"
                    value={newCamUrl}
                    onChange={(e) => setNewCamUrl(e.target.value)}
                    disabled={isRunning}
                  />
                  <button type="button" className="btn btn-block btn-sm" onClick={handleAddCamera} disabled={isRunning}>
                    <Plus {...ICON_SM} />
                    Thêm camera
                  </button>
                  <div className="camera-list">
                    {camerasList.map((cam) => (
                      <div key={cam.id} className="camera-item">
                        <div className="camera-item-body">
                          <div className="camera-item-name">{cam.name}</div>
                          <div className="camera-item-url">{cam.source_url}</div>
                        </div>
                        <div className="camera-item-actions">
                          <span className={`badge ${cam.status === 'ONLINE' ? 'success' : 'danger'}`}>{cam.status}</span>
                          <button type="button" className="btn-ghost btn-sm" onClick={() => testCamera(cam.id)}>
                            Kiểm tra
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>

            <div className="control-group control-group-divider">
              <span className="control-label">Lớp hiển thị</span>
              <div className="switch-label">
                <span>Khung người</span>
                <label className="switch">
                  <input type="checkbox" checked={showBboxes} onChange={(e) => setShowBboxes(e.target.checked)} />
                  <span className="slider" />
                </label>
              </div>
              <div className="switch-label">
                <span>Mã theo dõi</span>
                <label className="switch">
                  <input type="checkbox" checked={showTrackIds} onChange={(e) => setShowTrackIds(e.target.checked)} />
                  <span className="slider" />
                </label>
              </div>
              <div className="switch-label">
                <span>Vạch ảo</span>
                <label className="switch">
                  <input type="checkbox" checked={showLine} onChange={(e) => setShowLine(e.target.checked)} />
                  <span className="slider" />
                </label>
              </div>
            </div>

            <div className="panel-actions">
              <button type="button" className={`btn btn-block ${isRunning ? 'btn-danger' : ''}`} onClick={togglePipeline}>
                {isRunning ? (
                  <>
                    <Stop {...ICON} weight="fill" />
                    Dừng phân tích
                  </>
                ) : (
                  <>
                    <Play {...ICON} weight="fill" />
                    Bắt đầu phân tích
                  </>
                )}
              </button>
              <button type="button" className="btn btn-danger btn-block" onClick={resetStats}>
                <Trash {...ICON} />
                Xóa thống kê
              </button>
            </div>
          </section>

          <section className="panel video-panel">
            <h2 className="panel-title">
              <VideoCamera {...ICON} />
              Khung hình trực tiếp
            </h2>

            <div className={screenClass} data-testid="video-screen">
              <span className="screen-hud screen-hud--tl" aria-hidden="true" />
              <span className="screen-hud screen-hud--tr" aria-hidden="true" />
              <span className="screen-hud screen-hud--bl" aria-hidden="true" />
              <span className="screen-hud screen-hud--br" aria-hidden="true" />
              <span className="screen-scanline" aria-hidden="true" />
              <video
                ref={videoRef}
                className={`video-element ${sourceType === 'none' ? 'media-hidden' : ''} ${sourceType === 'webcam' ? 'is-mirrored' : ''}`}
                playsInline
                muted
                autoPlay
              />
              <canvas
                ref={overlayCanvasRef}
                className={`canvas-overlay ${sourceType === 'none' ? 'media-hidden' : ''}`}
                width={640}
                height={480}
                onMouseDown={handleMouseDown}
                onMouseMove={handleMouseMove}
                onMouseUp={handleMouseUp}
              />

              {sourceType !== 'none' && (
                <div className="video-counters">
                  <div className="video-counter entry">
                    <div className="video-counter-label">
                      <ArrowLineDownLeft size={12} weight="bold" />
                      Lượt vào
                    </div>
                    <div className={`video-counter-value ${animateEntry ? 'bump' : ''}`}>{entriesCount}</div>
                  </div>
                  <div className="video-counter exit">
                    <div className="video-counter-label">
                      <ArrowLineUpRight size={12} weight="bold" />
                      Lượt ra
                    </div>
                    <div className={`video-counter-value ${animateExit ? 'bump' : ''}`}>{exitsCount}</div>
                  </div>
                </div>
              )}

              {sourceType === 'none' && (
                <div className="screen-placeholder">
                  <div className="placeholder-radar" aria-hidden="true">
                    <span />
                    <span />
                    <span />
                  </div>
                  <VideoCamera size={48} weight="duotone" />
                  <div className="screen-placeholder-title">Chưa có nguồn video</div>
                  <div className="screen-placeholder-hint">Bật webcam hoặc tải video ở panel bên trái.</div>
                </div>
              )}
            </div>

            {sourceType !== 'none' && (
              <div className="video-counters video-counters--dock">
                <div className="video-counter entry">
                  <div className="video-counter-label">
                    <ArrowLineDownLeft size={12} weight="bold" />
                    Lượt vào
                  </div>
                  <div className={`video-counter-value ${animateEntry ? 'bump' : ''}`}>{entriesCount}</div>
                </div>
                <div className="video-counter exit">
                  <div className="video-counter-label">
                    <ArrowLineUpRight size={12} weight="bold" />
                    Lượt ra
                  </div>
                  <div className={`video-counter-value ${animateExit ? 'bump' : ''}`}>{exitsCount}</div>
                </div>
              </div>
            )}

            <div className="video-meta">
              <span>
                Đang theo dõi: <strong>{activeTracksCount}</strong>
              </span>
              <span>
                Tốc độ xử lý: <strong>{isRunning ? `${fps} FPS` : '0 FPS'}</strong>
              </span>
              <span>
                Latency: <strong>{isRunning ? `${responseLatencyMs} ms` : '0 ms'}</strong>
              </span>
              {!isRunning && sourceType !== 'none' && showLine && (
                <span className="video-meta-hint">Kéo chuột trên khung hình để vẽ vạch ảo</span>
              )}
            </div>
          </section>

          <section className="panel">
            <h2 className="panel-title">
              <FileText {...ICON} />
              Nhật ký hoạt động
            </h2>

            <div className="log-filters">
              {(['all', 'entry', 'exit', 'system'] as LogFilter[]).map((f) => (
                <button
                  key={f}
                  type="button"
                  className={`log-filter-btn ${logFilter === f ? 'active' : ''}`}
                  onClick={() => setLogFilter(f)}
                >
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
        </PageTransition>
      )}

      {activeTab === 'registry' && (
        <PageTransition key="registry" className="page-stack page-view" testId="view-registry">
          <section className="panel registry-form-panel">
            <h2 className="panel-title">
              <UserPlus {...ICON} />
              Đăng ký thành viên
            </h2>

            <form onSubmit={handleRegister} className="form-card">
              <div className="form-grid">
                <div className="control-group control-group-flush">
                  <span className="control-label">Họ và tên</span>
                  <input type="text" className="text-input" placeholder="Nguyễn Văn A" value={regName} onChange={(e) => setRegName(e.target.value)} required />
                </div>
                <div className="control-group control-group-flush">
                  <span className="control-label">Mã thẻ</span>
                  <input type="text" className="text-input" placeholder="SV123456" value={regCode} onChange={(e) => setRegCode(e.target.value)} required />
                </div>
                <div className="control-group control-group-flush">
                  <span className="control-label">Vai trò</span>
                  <select className="select-input" value={regRole} onChange={(e) => setRegRole(e.target.value)}>
                    <option value="STUDENT">Sinh viên</option>
                    <option value="FACULTY">Giảng viên</option>
                    <option value="STAFF">Nhân viên thư viện</option>
                    <option value="GUEST">Khách</option>
                  </select>
                </div>
                <div className="control-group control-group-flush">
                  <span className="control-label">Trạng thái</span>
                  <select className="select-input" value={regStatus} onChange={(e) => setRegStatus(e.target.value)}>
                    <option value="ACTIVE">Hoạt động</option>
                    <option value="INACTIVE">Ngưng</option>
                  </select>
                </div>
              </div>

              <div className="form-grid form-grid-actions registry-form-actions">
                <div className="control-group control-group-flush">
                  <span className="control-label">Ảnh chân dung</span>
                  <input type="file" accept="image/*" className="select-input" onChange={(e) => setRegPhoto(e.target.files?.[0] || null)} required />
                  <span className="field-hint">JPEG, PNG · Tối đa 10MB, tối thiểu 100×100px</span>
                </div>
                <button type="submit" className="btn form-submit-btn register-submit-btn">
                  <UserPlus {...ICON} />
                  Đăng ký
                </button>
              </div>
            </form>
          </section>

          <section className="panel panel-grow">
            <h2 className="panel-title">
              <Users {...ICON} />
              Danh sách thành viên
            </h2>

            {loadingRegistry ? (
              <SkeletonRows rows={6} />
            ) : (
            <div className="table-wrapper">
              <table className="data-table" data-testid="persons-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Họ tên</th>
                    <th>Mã thẻ</th>
                    <th>Vai trò</th>
                    <th>Trạng thái</th>
                    <th>Thao tác</th>
                  </tr>
                </thead>
                <tbody>
                  {persons.length === 0 ? (
                    <tr>
                      <td colSpan={6}>
                        <div className="empty-state">
                          <div className="empty-state-title">Chưa có thành viên</div>
                          Dùng form phía trên để đăng ký thành viên mới.
                        </div>
                      </td>
                    </tr>
                  ) : (
                    persons.map((p) => (
                      <tr key={p.id}>
                        <td className="mono">{p.id}</td>
                        <td className="cell-strong">{p.full_name}</td>
                        <td className="mono">{p.member_code}</td>
                        <td>{ROLE_LABELS[p.role] || p.role}</td>
                        <td>
                          <span className={`badge ${p.status === 'ACTIVE' ? 'success' : 'danger'}`}>
                            {p.status === 'ACTIVE' ? 'Hoạt động' : 'Ngưng'}
                          </span>
                        </td>
                        <td>
                          <div style={{ display: 'flex', gap: '8px' }}>
                            <button type="button" className="btn btn-sm" onClick={() => startEditPerson(p)}>
                              Sửa
                            </button>
                            <button type="button" className="btn btn-danger btn-sm" onClick={() => handleDeletePerson(p.id)}>
                              Xóa
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
            )}
          </section>
        </PageTransition>
      )}

      {activeTab === 'history' && (
        <PageTransition key="history" className="page-stack page-view" testId="view-history">
          <section className="panel panel-grow">
            <div className="section-toolbar">
              <h2 className="panel-title">
                <CalendarBlank {...ICON} />
                Lịch sử ra/vào
              </h2>
              <div className="toolbar-actions">
                <ExportMenu onExport={handleExport} disabled={loadingHistory} />
              </div>
            </div>

            <PeriodFilter
              preset={periodPreset}
              rangeLabel={activeRangeLabel}
              onPresetChange={applyPeriodPreset}
              fromDate={draftFrom}
              toDate={draftTo}
              onFromChange={setDraftFrom}
              onToChange={setDraftTo}
              onApply={applyCustomRange}
              applying={loadingHistory}
            />

            {loadingHistory ? (
              <SkeletonRows rows={8} />
            ) : (
            <div className="table-wrapper">
              <table className="data-table" data-testid="sessions-table">
                <thead>
                  <tr>
                    <th>Phiên</th>
                    <th>Tên</th>
                    <th>Mã thẻ</th>
                    <th>Giờ vào</th>
                    <th>Giờ ra</th>
                    <th>Thời lượng</th>
                    <th>Trạng thái</th>
                  </tr>
                </thead>
                <tbody>
                  {sessions.length === 0 ? (
                    <tr>
                      <td colSpan={7}>
                        <div className="empty-state">
                          <div className="empty-state-title">Chưa có phiên nào</div>
                          Không có dữ liệu trong khoảng {activeRangeLabel}.
                        </div>
                      </td>
                    </tr>
                  ) : (
                    sessions.map((s) => (
                      <tr key={s.id}>
                        <td className="mono">{s.id}</td>
                        <td className="cell-strong">{s.person_name}</td>
                        <td className="mono muted">{s.member_code || 'N/A'}</td>
                        <td>{s.entry_at ? new Date(s.entry_at).toLocaleString('vi-VN') : 'N/A'}</td>
                        <td>{s.exit_at ? new Date(s.exit_at).toLocaleString('vi-VN') : 'N/A'}</td>
                        <td className="mono">{s.duration_seconds !== null ? `${s.duration_seconds}s` : 'N/A'}</td>
                        <td>
                          <span className={`badge ${s.status === 'ACTIVE' ? 'warning' : 'success'}`}>
                            {s.status === 'ACTIVE' ? 'Đang trong' : 'Đã ra'}
                          </span>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
            )}
          </section>
        </PageTransition>
      )}

      {activeTab === 'analytics' && (
        <PageTransition key="analytics" className="page-stack page-view" testId="view-analytics">
          <div className="section-toolbar analytics-toolbar">
            <h2 className="panel-title">
              <ChartBar {...ICON} />
              Thống kê lưu lượng
            </h2>
            <div className="toolbar-actions">
              <ExportMenu onExport={handleExport} />
            </div>
          </div>

          <PeriodFilter
            preset={periodPreset}
            rangeLabel={activeRangeLabel}
            onPresetChange={applyPeriodPreset}
            fromDate={draftFrom}
            toDate={draftTo}
            onFromChange={setDraftFrom}
            onToChange={setDraftTo}
            onApply={applyCustomRange}
            applying={loadingAnalytics}
          />

          {loadingAnalytics ? (
            <>
              <SkeletonRows rows={3} />
              <SkeletonRows rows={6} />
            </>
          ) : (
          <>
          <div className="stats-primary-grid" data-testid="analytics-cards">
            <div className="stat-card">
              <div className="stat-card-label">Đang trong thư viện</div>
              <div className="stat-card-value occupancy">{occupancy.current_occupancy}</div>
            </div>
            <div className="stat-card">
              <div className="stat-card-label">Lượt vào</div>
              <div className="stat-card-value entry">{occupancy.total_entries_today}</div>
            </div>
            <div className="stat-card">
              <div className="stat-card-label">Lượt ra</div>
              <div className="stat-card-value exit">{occupancy.total_exits_today}</div>
            </div>
          </div>

          <div className="stat-card-meta">
            Khoảng <strong>{activeRangeLabel}</strong>
            {' · '}
            Đã biết <strong>{occupancy.known_visitors_today}</strong>
            {' · '}
            Khách <strong>{occupancy.unknown_visitors_today}</strong>
            {' · '}
            Tổng phiên <strong>{occupancy.total_sessions_today}</strong>
          </div>

          <section className="panel traffic-panel">
            <TrafficChart stats={hourlyStats} rangeLabel={activeRangeLabel} />
          </section>
          </>
          )}
        </PageTransition>
      )}
      {editingPerson && (
        <div className="modal-overlay" onClick={cancelEditPerson}>
          <div className="modal-container" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3 className="modal-title">
                <Pencil {...ICON} />
                Cập nhật thành viên
              </h3>
              <button type="button" className="modal-close-btn" onClick={cancelEditPerson}>
                <X size={18} />
              </button>
            </div>
            <div className="modal-body">
              <form onSubmit={handleUpdatePerson} className="form-card" style={{ boxShadow: 'none', padding: 0, border: 0 }}>
                <div className="form-grid" style={{ gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>
                  <div className="control-group control-group-flush">
                    <span className="control-label">Họ và tên</span>
                    <input type="text" className="text-input" placeholder="Nguyễn Văn A" value={editName} onChange={(e) => setEditName(e.target.value)} required />
                  </div>
                  <div className="control-group control-group-flush">
                    <span className="control-label">Mã thẻ</span>
                    <input type="text" className="text-input" placeholder="SV123456" value={editCode} onChange={(e) => setEditCode(e.target.value)} required />
                  </div>
                  <div className="control-group control-group-flush">
                    <span className="control-label">Vai trò</span>
                    <select className="select-input" value={editRole} onChange={(e) => setEditRole(e.target.value)}>
                      <option value="STUDENT">Sinh viên</option>
                      <option value="FACULTY">Giảng viên</option>
                      <option value="STAFF">Nhân viên thư viện</option>
                      <option value="GUEST">Khách</option>
                    </select>
                  </div>
                  <div className="control-group control-group-flush">
                    <span className="control-label">Trạng thái</span>
                    <select className="select-input" value={editStatus} onChange={(e) => setEditStatus(e.target.value)}>
                      <option value="ACTIVE">Hoạt động</option>
                      <option value="INACTIVE">Ngưng</option>
                    </select>
                  </div>
                </div>

                <div className="control-group" style={{ marginBottom: '20px' }}>
                  <span className="control-label">Ảnh chân dung mới (tùy chọn)</span>
                  <input type="file" accept="image/*" className="select-input" onChange={(e) => setEditPhoto(e.target.files?.[0] || null)} />
                  <span className="field-hint">Bỏ trống nếu giữ nguyên ảnh cũ · JPEG, PNG · Tối đa 10MB</span>
                </div>

                <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
                  <button type="button" className="btn btn-ghost" onClick={cancelEditPerson}>
                    Hủy
                  </button>
                  <button type="submit" className="btn form-submit-btn">
                    <Pencil {...ICON} />
                    Lưu thay đổi
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
      </AnimatePresence>
      </div>
    </>
  );
}

export default App;
