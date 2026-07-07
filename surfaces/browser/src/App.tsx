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
  DownloadSimple,
  ArrowsClockwise,
  Plus,
  Plugs,
} from '@phosphor-icons/react';
import { AnimatePresence } from 'framer-motion';
import { ToastContainer } from './components/Toast';
import { ThemeToggle } from './components/ThemeToggle';
import { NavTabs } from './components/NavTabs';
import { PageTransition } from './components/PageTransition';
import { SkeletonRows } from './components/Skeleton';
import { useToast } from './hooks/useToast';
import { readThemeColors, useTheme } from './hooks/useTheme';

interface Track {
  track_id: number;
  bbox: [number, number, number, number];
  confidence: number;
  person_name?: string;
  identity_type?: 'KNOWN' | 'UNKNOWN';
  similarity_score?: number;
}

interface CrossingEvent {
  track_id: number;
  direction: 'ENTRY' | 'EXIT';
  timestamp: number;
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
  const [isBackendOnline, setIsBackendOnline] = useState(false);
  const [sourceType, setSourceType] = useState<'webcam' | 'video' | 'none'>('none');
  const [isRunning, setIsRunning] = useState(false);
  const [fps, setFps] = useState(0);
  const [activeTracksCount, setActiveTracksCount] = useState(0);

  const [entriesCount, setEntriesCount] = useState(0);
  const [exitsCount, setExitsCount] = useState(0);
  const [logs, setLogs] = useState<LogItem[]>([]);

  const [showBboxes, setShowBboxes] = useState(true);
  const [showLine, setShowLine] = useState(true);
  const [showTrackIds, setShowTrackIds] = useState(true);

  const [lineConfig, setLineConfig] = useState<[[number, number], [number, number]]>([
    [100, 360],
    [540, 360],
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

  const [sessions, setSessions] = useState<VisitSession[]>([]);
  const [filterDate, setFilterDate] = useState<string>(new Date().toISOString().slice(0, 10));

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

  useEffect(() => {
    let active = true;
    const checkHealth = async () => {
      try {
        const res = await fetch(`${backendUrl}/api/health`);
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
    stopPipeline();
    stopCameraStream();
    clearOverlayCanvas();
  }, [sourceType]);

  useEffect(() => {
    if (activeTab === 'monitor') {
      loadCameras();
    } else if (activeTab === 'registry') {
      loadPersons();
    } else if (activeTab === 'history') {
      loadSessions();
    } else if (activeTab === 'analytics') {
      loadAnalytics();
    }
  }, [activeTab, backendUrl]);

  useEffect(() => {
    loadCameras();
  }, [backendUrl]);

  useEffect(() => {
    clearOverlayCanvas();
  }, [lineConfig, sourceType, showLine, theme]);

  const loadCameras = async () => {
    try {
      const res = await fetch(`${backendUrl}/api/cameras`);
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
      const res = await fetch(`${backendUrl}/api/cameras`, {
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
      const res = await fetch(`${backendUrl}/api/cameras/${id}/test`, { method: 'POST' });
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
      const res = await fetch(`${backendUrl}/api/persons`);
      if (res.ok) setPersons(await res.json());
    } catch (err) {
      console.error('Failed to load persons:', err);
      showToast('Không tải được danh sách thành viên.', 'error');
    } finally {
      setLoadingRegistry(false);
    }
  };

  const loadSessions = async () => {
    setLoadingHistory(true);
    try {
      const res = await fetch(`${backendUrl}/api/sessions`);
      if (res.ok) setSessions(await res.json());
    } catch (err) {
      console.error('Failed to load sessions:', err);
      showToast('Không tải được lịch sử phiên.', 'error');
    } finally {
      setLoadingHistory(false);
    }
  };

  const loadFilteredSessions = async () => {
    setLoadingHistory(true);
    try {
      const res = await fetch(`${backendUrl}/api/sessions?date=${filterDate}`);
      if (res.ok) setSessions(await res.json());
      else showToast('Không lọc được dữ liệu theo ngày.', 'error');
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
      const resOcc = await fetch(`${backendUrl}/api/stats/occupancy`);
      const resHourly = await fetch(`${backendUrl}/api/stats/hourly`);
      if (resOcc.ok && resHourly.ok) {
        setOccupancy(await resOcc.json());
        setHourlyStats(await resHourly.json());
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
      const res = await fetch(`${backendUrl}/api/persons/register`, {
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

  const handleDeletePerson = async (id: number) => {
    if (!window.confirm('Bạn có chắc muốn xóa thành viên này? Dữ liệu sinh trắc học sẽ bị xóa hoàn toàn.')) return;
    try {
      const res = await fetch(`${backendUrl}/api/persons/${id}`, { method: 'DELETE' });
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
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480, frameRate: 15 },
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play();
      }
      setSourceType('webcam');
      addLog('Đã kết nối webcam.', 'system');
    } catch (err) {
      showToast(`Không thể truy cập webcam: ${err}`, 'error');
      console.error(err);
    }
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
    if (isRunning) stopPipeline();
    else startPipeline();
  };

  const startPipeline = () => {
    if (sourceType === 'none') {
      showToast('Hãy kết nối webcam hoặc tải video trước.', 'error');
      return;
    }
    setIsRunning(true);
    lastFrameTimeRef.current = performance.now();
    sessionTrackerIdRef.current = `session_${Math.floor(Date.now() / 1000)}`;
    addLog(`Bắt đầu phân tích (phiên ${sessionTrackerIdRef.current})`, 'system');
    scheduleNextFrame();
  };

  const stopPipeline = () => {
    if (!isRunning && loopTimeoutRef.current === null) return;
    setIsRunning(false);
    if (loopTimeoutRef.current !== null) {
      clearTimeout(loopTimeoutRef.current);
      loopTimeoutRef.current = null;
    }
    if (isRunning) addLog('Đã dừng phân tích.', 'system');
  };

  const scheduleNextFrame = () => {
    if (loopTimeoutRef.current !== null) clearTimeout(loopTimeoutRef.current);
    loopTimeoutRef.current = window.setTimeout(async () => {
      if (!isRunning) return;
      await processCurrentFrame();
      scheduleNextFrame();
    }, 100);
  };

  const processCurrentFrame = async () => {
    const video = videoRef.current;
    if (!video || video.paused || video.ended) return;

    const offscreenCanvas = document.createElement('canvas');
    offscreenCanvas.width = 640;
    offscreenCanvas.height = 480;
    const ctx = offscreenCanvas.getContext('2d');
    if (!ctx) return;

    ctx.drawImage(video, 0, 0, 640, 480);

    const blob = await new Promise<Blob | null>((resolve) => {
      offscreenCanvas.toBlob((b) => resolve(b), 'image/jpeg', 0.85);
    });
    if (!blob) return;

    const formData = new FormData();
    formData.append('file', blob, 'frame.jpg');
    formData.append('session_id', sessionTrackerIdRef.current);
    formData.append('line_config', JSON.stringify(lineConfig));

    try {
      const response = await fetch(`${backendUrl}/api/process-frame`, {
        method: 'POST',
        body: formData,
      });
      if (!response.ok) throw new Error('API server returned error');

      const result = await response.json();
      const endTime = performance.now();
      setFps(Math.round(1000 / (endTime - lastFrameTimeRef.current)));
      lastFrameTimeRef.current = endTime;

      const tracks: Track[] = result.tracks || [];
      const crossingEvents: CrossingEvent[] = result.crossing_events || [];

      setActiveTracksCount(tracks.length);
      drawOverlay(tracks);
      handleCrossingEvents(tracks, crossingEvents);
    } catch (err) {
      console.error('Frame processing failed:', err);
    }
  };

  const drawOverlay = (tracks: Track[]) => {
    const canvas = overlayCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const colors = readThemeColors();

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (showLine) {
      const [p1, p2] = lineConfig;
      ctx.beginPath();
      ctx.moveTo(p1[0], p1[1]);
      ctx.lineTo(p2[0], p2[1]);
      ctx.lineWidth = 3;
      ctx.strokeStyle = colors.accent;
      ctx.stroke();

      ctx.fillStyle = colors.accent;
      ctx.beginPath();
      ctx.arc(p1[0], p1[1], 5, 0, Math.PI * 2);
      ctx.arc(p2[0], p2[1], 5, 0, Math.PI * 2);
      ctx.fill();

      ctx.font = '600 11px Outfit, sans-serif';
      ctx.fillStyle = colors.accent;
      ctx.fillText('Hướng vào', (p1[0] + p2[0]) / 2 - 28, (p1[1] + p2[1]) / 2 - 10);
    }

    if (showBboxes) {
      tracks.forEach((track) => {
        const [x1, y1, x2, y2] = track.bbox;
        const width = x2 - x1;
        const height = y2 - y1;
        const isKnown = track.identity_type === 'KNOWN';
        const color = isKnown ? colors.entry : colors.exit;

        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.strokeRect(x1, y1, width, height);
        ctx.fillStyle = isKnown ? colors.entryFill : colors.exitFill;
        ctx.fillRect(x1, y1, width, height);

        if (showTrackIds) {
          const name = isKnown ? track.person_name : 'Khách';
          const label = `#${track.track_id} ${name}`;
          ctx.font = '600 11px JetBrains Mono, monospace';
          const textWidth = ctx.measureText(label).width;
          ctx.fillStyle = color;
          ctx.fillRect(x1, y1 - 20, textWidth + 10, 20);
          ctx.fillStyle = colors.labelFg;
          ctx.fillText(label, x1 + 4, y1 - 5);
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
      const name = track?.person_name || 'Khách';
      const type = track?.identity_type || 'UNKNOWN';

      if (event.direction === 'ENTRY') {
        setEntriesCount((prev) => prev + 1);
        triggerCounterPulse('entry');
        addLog(`Vào: ${name} (${type === 'KNOWN' ? 'đã biết' : 'khách'}) #${event.track_id}`, 'entry');
      } else if (event.direction === 'EXIT') {
        setExitsCount((prev) => prev + 1);
        triggerCounterPulse('exit');
        addLog(`Ra: ${name} (${type === 'KNOWN' ? 'đã biết' : 'khách'}) #${event.track_id}`, 'exit');
      }
    });
  };

  const clearOverlayCanvas = () => {
    const canvas = overlayCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const colors = readThemeColors();
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (sourceType !== 'none' && showLine) {
      const [p1, p2] = lineConfig;
      ctx.beginPath();
      ctx.moveTo(p1[0], p1[1]);
      ctx.lineTo(p2[0], p2[1]);
      ctx.lineWidth = 3;
      ctx.strokeStyle = colors.accent;
      ctx.stroke();
      ctx.fillStyle = colors.accent;
      ctx.beginPath();
      ctx.arc(p1[0], p1[1], 5, 0, Math.PI * 2);
      ctx.arc(p2[0], p2[1], 5, 0, Math.PI * 2);
      ctx.fill();
    }
  };

  const getMouseCoords = (e: React.MouseEvent<HTMLCanvasElement>): [number, number] => {
    const canvas = overlayCanvasRef.current;
    if (!canvas) return [0, 0];
    const rect = canvas.getBoundingClientRect();
    const x = Math.round(((e.clientX - rect.left) / rect.width) * canvas.width);
    const y = Math.round(((e.clientY - rect.top) / rect.height) * canvas.height);
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

  const exportToCSV = () => {
    if (sessions.length === 0) {
      showToast('Không có dữ liệu phiên để xuất.', 'error');
      return;
    }
    const headers = ['Session ID', 'Person Name', 'Member Code', 'Identity Type', 'Entry Time', 'Exit Time', 'Duration (s)', 'Status'];
    const rows = sessions.map((s) => [
      s.id,
      s.person_name || '',
      s.member_code || '',
      s.person_name && s.person_name.startsWith('UNKNOWN_') ? 'UNKNOWN' : 'KNOWN',
      s.entry_at ? new Date(s.entry_at).toLocaleString('vi-VN') : '',
      s.exit_at ? new Date(s.exit_at).toLocaleString('vi-VN') : '',
      s.duration_seconds !== null ? s.duration_seconds : '',
      s.status,
    ]);
    const csvContent = [headers, ...rows].map((r) => r.map((v) => `"${v}"`).join(',')).join('\n');
    const blob = new Blob(['\uFEFF' + csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `libcounterai_sessions_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    showToast('Đã xuất báo cáo CSV.', 'success');
  };

  const maxHourlyVolume = Math.max(...hourlyStats.map((s) => s.entry + s.exit), 1);
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

      <AnimatePresence mode="sync" initial={false}>
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
                <button type="button" className="btn btn-block" onClick={startWebcam} disabled={isRunning}>
                  <Camera {...ICON} />
                  Bật webcam
                </button>
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
                    <div className="file-dropzone-hint">MP4, WebM, AVI</div>
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
                className={`video-element ${sourceType === 'none' ? 'media-hidden' : ''}`}
                playsInline
                muted
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

            <div className="video-meta">
              <span>
                Đang theo dõi: <strong>{activeTracksCount}</strong>
              </span>
              <span>
                Tốc độ xử lý: <strong>{isRunning ? `${fps} FPS` : '0 FPS'}</strong>
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
          <section className="panel">
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

              <div className="form-grid form-grid-actions">
                <div className="control-group control-group-flush">
                  <span className="control-label">Ảnh chân dung</span>
                  <input type="file" accept="image/*" className="select-input" onChange={(e) => setRegPhoto(e.target.files?.[0] || null)} required />
                </div>
                <button type="submit" className="btn form-submit-btn">
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
                          <button type="button" className="btn btn-danger btn-sm" onClick={() => handleDeletePerson(p.id)}>
                            Xóa
                          </button>
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
                <input
                  type="date"
                  className="text-input text-input-date"
                  value={filterDate}
                  onChange={(e) => setFilterDate(e.target.value)}
                />
                <button type="button" className="btn btn-sm" onClick={loadFilteredSessions}>
                  <ArrowsClockwise {...ICON_SM} />
                  Lọc
                </button>
                <button type="button" className="btn btn-sm" data-testid="export-csv" onClick={exportToCSV}>
                  <DownloadSimple {...ICON_SM} />
                  Xuất CSV
                </button>
              </div>
            </div>

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
                          Dữ liệu sẽ xuất hiện khi có sự kiện ra/vào.
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
              <div className="stat-card-label">Lượt vào hôm nay</div>
              <div className="stat-card-value entry">{occupancy.total_entries_today}</div>
            </div>
            <div className="stat-card">
              <div className="stat-card-label">Lượt ra hôm nay</div>
              <div className="stat-card-value exit">{occupancy.total_exits_today}</div>
            </div>
          </div>

          <div className="stat-card-meta">
            Đã biết <strong>{occupancy.known_visitors_today}</strong>
            {' · '}
            Khách <strong>{occupancy.unknown_visitors_today}</strong>
            {' · '}
            Tổng phiên <strong>{occupancy.total_sessions_today}</strong>
          </div>

          <section className="panel">
            <h2 className="panel-title">
              <ChartBar {...ICON} />
              Lưu lượng theo giờ
            </h2>

            <div className="hourly-chart">
              {hourlyStats.filter((s) => s.entry > 0 || s.exit > 0).length === 0 ? (
                <div className="empty-state">Chưa có dữ liệu lưu lượng hôm nay.</div>
              ) : (
                hourlyStats.map((s) => {
                  const entryPct = (s.entry / maxHourlyVolume) * 100;
                  const exitPct = (s.exit / maxHourlyVolume) * 100;
                  return (
                    <div key={s.hour} className="chart-row">
                      <div className="chart-hour">{s.hour.toString().padStart(2, '0')}:00</div>
                      <div className="chart-bars-container">
                        {s.entry > 0 && (
                          <div className="bar-wrapper">
                            <div className="bar-fill entry" style={{ ['--bar-pct' as string]: `${entryPct}%` }} />
                            <span className="bar-val">{s.entry} vào</span>
                          </div>
                        )}
                        {s.exit > 0 && (
                          <div className="bar-wrapper">
                            <div className="bar-fill exit" style={{ ['--bar-pct' as string]: `${exitPct}%` }} />
                            <span className="bar-val">{s.exit} ra</span>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </section>
          </>
          )}
        </PageTransition>
      )}
      </AnimatePresence>
    </>
  );
}

export default App;
