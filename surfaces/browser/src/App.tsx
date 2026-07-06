import React, { useState, useEffect, useRef } from 'react';
import './App.css';

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

function App() {
  // Navigation
  const [activeTab, setActiveTab] = useState<'monitor' | 'registry' | 'history' | 'analytics'>('monitor');

  // Settings & Status States
  const [backendUrl, setBackendUrl] = useState('http://localhost:8000');
  const [isBackendOnline, setIsBackendOnline] = useState(false);
  const [sourceType, setSourceType] = useState<'webcam' | 'video' | 'none'>('none');
  const [isRunning, setIsRunning] = useState(false);
  const [fps, setFps] = useState(0);
  const [activeTracksCount, setActiveTracksCount] = useState(0);
  
  // Counters & Event Logs
  const [entriesCount, setEntriesCount] = useState(0);
  const [exitsCount, setExitsCount] = useState(0);
  const [logs, setLogs] = useState<LogItem[]>([]);
  
  // Overlay Toggles
  const [showBboxes, setShowBboxes] = useState(true);
  const [showLine, setShowLine] = useState(true);
  const [showTrackIds, setShowTrackIds] = useState(true);
  
  // Interactive Line Coordinates (relative to 640x480 resolution)
  const [lineConfig, setLineConfig] = useState<[[number, number], [number, number]]>([
    [100, 360],
    [540, 360]
  ]);
  const [isDrawing, setIsDrawing] = useState(false);
  
  // Animation flags for counters
  const [animateEntry, setAnimateEntry] = useState(false);
  const [animateExit, setAnimateExit] = useState(false);

  // Registry States
  const [persons, setPersons] = useState<Person[]>([]);
  const [regName, setRegName] = useState('');
  const [regCode, setRegCode] = useState('');
  const [regRole, setRegRole] = useState('STUDENT');
  const [regStatus, setRegStatus] = useState('ACTIVE');
  const [regPhoto, setRegPhoto] = useState<File | null>(null);

  // History States
  const [sessions, setSessions] = useState<VisitSession[]>([]);

  // Analytics States
  const [occupancy, setOccupancy] = useState<OccupancyStats>({ current_occupancy: 0, total_entries_today: 0, total_exits_today: 0, known_visitors_today: 0, unknown_visitors_today: 0, total_sessions_today: 0 });
  const [hourlyStats, setHourlyStats] = useState<HourlyStat[]>([]);

  // Camera Management States
  const [camerasList, setCamerasList] = useState<any[]>([]);
  const [newCamName, setNewCamName] = useState('');
  const [newCamUrl, setNewCamUrl] = useState('');

  // References
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const overlayCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const loopTimeoutRef = useRef<number | null>(null);
  const sessionTrackerIdRef = useRef<string>(`session_${Math.floor(Date.now() / 1000)}`);
  const streamRef = useRef<MediaStream | null>(null);
  const lastFrameTimeRef = useRef<number>(0);

  // 1. Health check the backend on mount and when URL changes
  useEffect(() => {
    let active = true;
    const checkHealth = async () => {
      try {
        const res = await fetch(`${backendUrl}/api/health`);
        if (res.ok && active) {
          setIsBackendOnline(true);
        } else if (active) {
          setIsBackendOnline(false);
        }
      } catch (err) {
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

  // 2. Stop camera stream and clear processing loops when sourceType changes
  useEffect(() => {
    stopPipeline();
    stopCameraStream();
    clearOverlayCanvas();
  }, [sourceType]);

  // 3. Tab switching side-effects
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

  const loadCameras = async () => {
    try {
      const res = await fetch(`${backendUrl}/api/cameras`);
      if (res.ok) {
        setCamerasList(await res.json());
      }
    } catch (err) {
      console.error("Failed to load cameras: ", err);
    }
  };

  const handleAddCamera = async () => {
    if (!newCamName || !newCamUrl) {
      alert("Vui lòng nhập tên camera và địa chỉ kết nối.");
      return;
    }
    try {
      const res = await fetch(`${backendUrl}/api/cameras`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: newCamName,
          source_type: "RTSP",
          source_url: newCamUrl
        })
      });
      if (res.ok) {
        alert("Thêm camera mạng thành công!");
        setNewCamName("");
        setNewCamUrl("");
        loadCameras();
      } else {
        const err = await res.json();
        alert(`Thêm camera thất bại: ${err.detail || 'Lỗi không xác định'}`);
      }
    } catch (err) {
      alert("Không thể kết nối đến máy chủ API.");
    }
  };

  const testCamera = async (id: number) => {
    try {
      const res = await fetch(`${backendUrl}/api/cameras/${id}/test`, { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        alert(`Kiểm tra kết nối thành công: ${data.status}`);
        loadCameras();
      } else {
        alert("Lỗi khi kiểm tra kết nối.");
      }
    } catch (err) {
      alert("Không thể kết nối đến máy chủ API.");
    }
  };

  const loadPersons = async () => {
    try {
      const res = await fetch(`${backendUrl}/api/persons`);
      if (res.ok) {
        const data = await res.json();
        setPersons(data);
      }
    } catch (err) {
      console.error("Failed to load persons: ", err);
    }
  };

  const loadSessions = async () => {
    try {
      const res = await fetch(`${backendUrl}/api/sessions`);
      if (res.ok) {
        const data = await res.json();
        setSessions(data);
      }
    } catch (err) {
      console.error("Failed to load sessions: ", err);
    }
  };

  const loadAnalytics = async () => {
    try {
      const resOcc = await fetch(`${backendUrl}/api/stats/occupancy`);
      const resHourly = await fetch(`${backendUrl}/api/stats/hourly`);
      if (resOcc.ok && resHourly.ok) {
        setOccupancy(await resOcc.json());
        setHourlyStats(await resHourly.json());
      }
    } catch (err) {
      console.error("Failed to load analytics: ", err);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!regName || !regCode || !regRole || !regPhoto) {
      alert("Vui lòng điền đầy đủ thông tin và chọn ảnh chân dung.");
      return;
    }
    const formData = new FormData();
    formData.append("full_name", regName);
    formData.append("member_code", regCode);
    formData.append("role", regRole);
    formData.append("status", regStatus);
    formData.append("file", regPhoto);

    try {
      const res = await fetch(`${backendUrl}/api/persons/register`, {
        method: "POST",
        body: formData
      });
      if (!res.ok) {
        const err = await res.json();
        alert(`Đăng ký thất bại: ${err.detail || 'Lỗi không xác định'}`);
        return;
      }
      alert("Đăng ký thành viên mới thành công!");
      setRegName("");
      setRegCode("");
      setRegRole("STUDENT");
      setRegStatus("ACTIVE");
      setRegPhoto(null);
      loadPersons();
    } catch (err) {
      alert(`Lỗi kết nối backend: ${err}`);
    }
  };

  const handleDeletePerson = async (id: number) => {
    if (!window.confirm("Bạn có chắc chắn muốn xóa thành viên này? Các dữ liệu sinh trắc học sẽ bị xóa hoàn toàn.")) return;
    try {
      const res = await fetch(`${backendUrl}/api/persons/${id}`, {
        method: "DELETE"
      });
      if (res.ok) {
        loadPersons();
      } else {
        alert("Xóa thành viên thất bại.");
      }
    } catch (err) {
      alert(`Lỗi kết nối: ${err}`);
    }
  };

  const stopCameraStream = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
  };

  const startWebcam = async () => {
    try {
      stopCameraStream();
      const constraints = {
        video: { width: 640, height: 480, frameRate: 15 }
      };
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play();
      }
      setSourceType('webcam');
      addLog('Connected to system webcam source successfully.', 'system');
    } catch (err) {
      alert('Could not access webcam: ' + err);
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
      addLog(`Loaded sample video: ${file.name}`, 'system');
    }
  };

  const togglePipeline = () => {
    if (isRunning) {
      stopPipeline();
    } else {
      startPipeline();
    }
  };

  const startPipeline = () => {
    if (sourceType === 'none') {
      alert('Please connect webcam or upload video first.');
      return;
    }
    setIsRunning(true);
    lastFrameTimeRef.current = performance.now();
    sessionTrackerIdRef.current = `session_${Math.floor(Date.now() / 1000)}`;
    addLog(`Stream Analysis started (Session ID: ${sessionTrackerIdRef.current})`, 'system');
    scheduleNextFrame();
  };

  const stopPipeline = () => {
    setIsRunning(false);
    if (loopTimeoutRef.current !== null) {
      clearTimeout(loopTimeoutRef.current);
      loopTimeoutRef.current = null;
    }
    addLog('Stream Analysis stopped.', 'system');
  };

  const scheduleNextFrame = () => {
    if (loopTimeoutRef.current !== null) {
      clearTimeout(loopTimeoutRef.current);
    }
    loopTimeoutRef.current = window.setTimeout(async () => {
      if (!isRunning) return;
      await processCurrentFrame();
      scheduleNextFrame();
    }, 100); // 100ms interval
  };

  // Extract canvas frame and upload to FastAPI backend
  const processCurrentFrame = async () => {
    const video = videoRef.current;
    if (!video || video.paused || video.ended) return;

    // Create an offscreen canvas to capture the current frame
    const offscreenCanvas = document.createElement('canvas');
    offscreenCanvas.width = 640;
    offscreenCanvas.height = 480;
    const ctx = offscreenCanvas.getContext('2d');
    if (!ctx) return;

    // Draw the current video frame (supporting 1:1 scale mapped to 640x480)
    ctx.drawImage(video, 0, 0, 640, 480);

    // Convert offscreen canvas to JPEG blob
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
        body: formData
      });

      if (!response.ok) {
        throw new Error('API server returned error');
      }

      const result = await response.json();
      const endTime = performance.now();

      // Calculate real-time processing FPS
      const currentFps = Math.round(1000 / (endTime - lastFrameTimeRef.current));
      setFps(currentFps);
      lastFrameTimeRef.current = endTime;

      const tracks: Track[] = result.tracks || [];
      const crossingEvents: CrossingEvent[] = result.crossing_events || [];

      setActiveTracksCount(tracks.length);
      
      // Update UI with tracks and events
      drawOverlay(tracks);
      handleCrossingEvents(tracks, crossingEvents);

    } catch (err) {
      console.error('Frame processing failed: ', err);
    }
  };

  // Draw detected boxes, labels, and the virtual line on the overlay canvas
  const drawOverlay = (tracks: Track[]) => {
    const canvas = overlayCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear previous frame overlays
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // 1. Draw virtual line if enabled
    if (showLine) {
      const [p1, p2] = lineConfig;
      ctx.beginPath();
      ctx.moveTo(p1[0], p1[1]);
      ctx.lineTo(p2[0], p2[1]);
      ctx.lineWidth = 4;
      ctx.strokeStyle = '#45f3ff'; // Neon cyan
      ctx.stroke();

      // Draw virtual line terminals (caps)
      ctx.fillStyle = '#45f3ff';
      ctx.beginPath();
      ctx.arc(p1[0], p1[1], 6, 0, Math.PI * 2);
      ctx.arc(p2[0], p2[1], 6, 0, Math.PI * 2);
      ctx.fill();

      // Label directions
      ctx.font = 'bold 11px Outfit, sans-serif';
      ctx.fillStyle = '#45f3ff';
      ctx.fillText('ENTRY DIRECTION →', (p1[0] + p2[0]) / 2 - 50, (p1[1] + p2[1]) / 2 - 10);
    }

    // 2. Draw active tracked bounding boxes
    if (showBboxes) {
      tracks.forEach((track) => {
        const [x1, y1, x2, y2] = track.bbox;
        const width = x2 - x1;
        const height = y2 - y1;

        // Colors based on identity type
        const isKnown = track.identity_type === 'KNOWN';
        const color = isKnown ? '#00ff87' : '#ff007f'; // Green for KNOWN, Pink for UNKNOWN/UNRESOLVED

        // Bounding box border
        ctx.strokeStyle = color;
        ctx.lineWidth = 2.5;
        ctx.strokeRect(x1, y1, width, height);

        // Semi-transparent filling
        ctx.fillStyle = isKnown ? 'rgba(0, 255, 135, 0.05)' : 'rgba(255, 0, 127, 0.05)';
        ctx.fillRect(x1, y1, width, height);

        // Bounding Box Header tag
        if (showTrackIds) {
          const name = isKnown ? track.person_name : 'Unknown';
          const label = `ID: ${track.track_id} | ${name}`;
          ctx.font = 'bold 12px JetBrains Mono, monospace';
          const textWidth = ctx.measureText(label).width;
          
          ctx.fillStyle = color;
          ctx.fillRect(x1 - 1, y1 - 22, textWidth + 12, 22);

          ctx.fillStyle = '#0d0f14';
          ctx.fillText(label, x1 + 5, y1 - 6);
        }
      });
    }
  };

  // Update counters and logs based on crossing events
  const handleCrossingEvents = (tracks: Track[], events: CrossingEvent[]) => {
    events.forEach((event) => {
      // Find matching track for name
      const track = tracks.find(t => t.track_id === event.track_id);
      const name = track?.person_name || 'Unknown';
      const type = track?.identity_type || 'UNKNOWN';

      if (event.direction === 'ENTRY') {
        setEntriesCount((prev) => prev + 1);
        setAnimateEntry(true);
        setTimeout(() => setAnimateEntry(false), 300);
        addLog(`[ENTRY] ${name} (${type}) passed entry gate (Track ID #${event.track_id})`, 'entry');
      } else if (event.direction === 'EXIT') {
        setExitsCount((prev) => prev + 1);
        setAnimateExit(true);
        setTimeout(() => setAnimateExit(false), 300);
        addLog(`[EXIT] ${name} (${type}) passed exit gate (Track ID #${event.track_id})`, 'exit');
      }
    });
  };

  const clearOverlayCanvas = () => {
    const canvas = overlayCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (ctx) {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      
      // Draw virtual line static preview if camera is connected but analysis loop is off
      if (sourceType !== 'none' && showLine) {
        const [p1, p2] = lineConfig;
        ctx.beginPath();
        ctx.moveTo(p1[0], p1[1]);
        ctx.lineTo(p2[0], p2[1]);
        ctx.lineWidth = 4;
        ctx.strokeStyle = '#45f3ff';
        ctx.stroke();
        ctx.fillStyle = '#45f3ff';
        ctx.beginPath();
        ctx.arc(p1[0], p1[1], 6, 0, Math.PI * 2);
        ctx.arc(p2[0], p2[1], 6, 0, Math.PI * 2);
        ctx.fill();
      }
    }
  };

  // Canvas Interactive line configuration via mouse actions
  const getMouseCoords = (e: React.MouseEvent<HTMLCanvasElement>): [number, number] => {
    const canvas = overlayCanvasRef.current;
    if (!canvas) return [0, 0];
    const rect = canvas.getBoundingClientRect();
    // Scale coords to match actual canvas resolution 640x480
    const x = Math.round(((e.clientX - rect.left) / rect.width) * canvas.width);
    const y = Math.round(((e.clientY - rect.top) / rect.height) * canvas.height);
    return [x, y];
  };

  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!showLine || isRunning) return; // Prevent line change when analysis is active
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
    setIsDrawing(false);
    addLog(`Virtual line configured: [(${lineConfig[0].join(',')}) → (${lineConfig[1].join(',')})]`, 'system');
  };

  // Draw initial preview line on mount
  useEffect(() => {
    clearOverlayCanvas();
  }, [lineConfig, sourceType]);

  const addLog = (text: string, type: 'entry' | 'exit' | 'system') => {
    const time = new Date().toLocaleTimeString();
    const item: LogItem = {
      id: Math.random().toString(36).substr(2, 9),
      time,
      text,
      type
    };
    setLogs((prev) => [item, ...prev].slice(0, 50));
  };

  const resetStats = () => {
    setEntriesCount(0);
    setExitsCount(0);
    setLogs([]);
    addLog('Statistics and memory logs cleared.', 'system');
  };

  // E04: CSV Export for visit sessions
  const exportToCSV = () => {
    if (sessions.length === 0) {
      alert('Không có dữ liệu phiên để xuất báo cáo.');
      return;
    }
    const headers = ['Session ID', 'Person Name', 'Member Code', 'Identity Type', 'Entry Time', 'Exit Time', 'Duration (s)', 'Status'];
    const rows = sessions.map(s => [
      s.id,
      s.person_name || '',
      s.member_code || '',
      (s.person_name && s.person_name.startsWith('UNKNOWN_')) ? 'UNKNOWN' : 'KNOWN',
      s.entry_at ? new Date(s.entry_at).toLocaleString() : '',
      s.exit_at ? new Date(s.exit_at).toLocaleString() : '',
      s.duration_seconds !== null ? s.duration_seconds : '',
      s.status
    ]);
    const csvContent = [headers, ...rows].map(r => r.map(v => `"${v}"`).join(',')).join('\n');
    const blob = new Blob(['\uFEFF' + csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `libcounterai_sessions_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    addLog('Session report exported to CSV.', 'system');
  };

  // E04: Date-based filtering for sessions API
  const [filterDate, setFilterDate] = useState<string>(new Date().toISOString().slice(0, 10));

  const loadFilteredSessions = async () => {
    try {
      const res = await fetch(`${backendUrl}/api/sessions?date=${filterDate}`);
      if (res.ok) {
        setSessions(await res.json());
      }
    } catch (err) {
      console.error("Failed to load filtered sessions: ", err);
    }
  };

  const maxHourlyVolume = Math.max(...hourlyStats.map(s => s.entry + s.exit), 1);

  return (
    <>
      {/* Header */}
      <header className="app-header">
        <div className="brand">
          <div className="brand-icon">L</div>
          <div>
            <h1 className="brand-name">LibCounterAI <span className="brand-badge">Epic E02</span></h1>
          </div>
        </div>

        {/* Tab Selection */}
        <nav className="nav-tabs" style={{marginBottom: 0}}>
          <button className={`tab-btn ${activeTab === 'monitor' ? 'active' : ''}`} onClick={() => setActiveTab('monitor')}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M23 7a2 2 0 0 0-2.45-1.45L16 7V5a2 2 0 0 0-2-2H2a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2l4.55 1.45A2 2 0 0 0 23 17V7z"/></svg>
            Live Monitor
          </button>
          <button className={`tab-btn ${activeTab === 'registry' ? 'active' : ''}`} onClick={() => setActiveTab('registry')}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
            Member Registry
          </button>
          <button className={`tab-btn ${activeTab === 'history' ? 'active' : ''}`} onClick={() => setActiveTab('history')}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
            Visit Sessions
          </button>
          <button className={`tab-btn ${activeTab === 'analytics' ? 'active' : ''}`} onClick={() => setActiveTab('analytics')}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
            Analytics & Reports
          </button>
        </nav>

        <div className="system-status">
          <div className="status-indicator">
            Server:
            <span className={`dot ${isBackendOnline ? 'online' : 'offline'}`}></span>
            {isBackendOnline ? 'Online' : 'Offline'}
          </div>
        </div>
      </header>

      {/* MONITOR TAB */}
      {activeTab === 'monitor' && (
        <main className="dashboard-grid">
          {/* Controls */}
          <section className="glass-panel">
            <h2 className="panel-title">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.1a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>
              System Controls
            </h2>
            
            <div className="control-group">
              <span className="control-label">API SERVER URL</span>
              <input 
                type="text" 
                className="text-input" 
                value={backendUrl} 
                onChange={(e) => setBackendUrl(e.target.value)} 
                disabled={isRunning}
              />
            </div>

            <div className="control-group">
              <span className="control-label">CAMERA SOURCE</span>
              <button className="btn" onClick={startWebcam} disabled={isRunning} style={{marginBottom: '8px'}}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>
                Start Webcam
              </button>
              <div className="file-dropzone">
                <input 
                  type="file" 
                  id="file-upload" 
                  accept="video/*" 
                  style={{display: 'none'}} 
                  onChange={handleVideoUpload}
                  disabled={isRunning}
                />
                <label htmlFor="file-upload" style={{cursor: isRunning ? 'not-allowed' : 'pointer', width: '100%'}}>
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
                  <div style={{fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)', marginTop: '4px'}}>Upload Sample Video</div>
                  <div style={{fontSize: '11px', color: 'var(--text-muted)'}}>MP4, WebM, AVI</div>
                </label>
              </div>
            </div>

            <div className="control-group" style={{borderTop: '1px solid var(--border-color)', paddingTop: '16px'}}>
              <span className="control-label">RTSP Network Cameras</span>
              <div style={{display: 'flex', flexDirection: 'column', gap: '8px'}}>
                <input 
                  type="text" 
                  className="text-input" 
                  placeholder="Camera Name (e.g. Front Gate)"
                  value={newCamName}
                  onChange={(e) => setNewCamName(e.target.value)}
                  disabled={isRunning}
                  style={{fontSize: '13px'}}
                />
                <input 
                  type="text" 
                  className="text-input" 
                  placeholder="URL (e.g. rtsp://...)"
                  value={newCamUrl}
                  onChange={(e) => setNewCamUrl(e.target.value)}
                  disabled={isRunning}
                  style={{fontSize: '13px'}}
                />
                <button className="btn" onClick={handleAddCamera} disabled={isRunning} style={{padding: '8px 12px', fontSize: '13px'}}>
                  Add Network Camera
                </button>
              </div>

              {/* Active Cameras List */}
              <div style={{marginTop: '12px', display: 'flex', flexDirection: 'column', gap: '6px', maxHeight: '180px', overflowY: 'auto'}}>
                {camerasList.map(cam => (
                  <div key={cam.id} style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(255,255,255,0.02)', padding: '6px 10px', borderRadius: '6px', border: '1px solid var(--border-color)'}}>
                    <div style={{fontSize: '11px', overflow: 'hidden', marginRight: '6px'}}>
                      <div style={{fontWeight: 600, color: 'var(--text-primary)', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap'}}>{cam.name}</div>
                      <div style={{color: 'var(--text-muted)', fontSize: '9px', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap'}}>{cam.source_url}</div>
                    </div>
                    <div style={{display: 'flex', alignItems: 'center', gap: '6px'}}>
                      <span className={`badge ${cam.status === 'ONLINE' ? 'success' : 'danger'}`} style={{fontSize: '8px', padding: '1px 4px'}}>
                        {cam.status}
                      </span>
                      <button style={{background: 'none', border: 'none', color: 'var(--accent-cyan)', cursor: 'pointer', fontSize: '10px'}} onClick={() => testCamera(cam.id)}>
                        Test
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="control-group" style={{borderTop: '1px solid var(--border-color)', paddingTop: '16px'}}>
              <span className="control-label">OVERLAY FILTERS</span>
              <label className="switch-label">
                Show Person Boxes
                <label className="switch">
                  <input type="checkbox" checked={showBboxes} onChange={(e) => setShowBboxes(e.target.checked)} />
                  <span className="slider"></span>
                </label>
              </label>
              <label className="switch-label">
                Show Tracking IDs
                <label className="switch">
                  <input type="checkbox" checked={showTrackIds} onChange={(e) => setShowTrackIds(e.target.checked)} />
                  <span className="slider"></span>
                </label>
              </label>
              <label className="switch-label">
                Show Virtual Line
                <label className="switch">
                  <input type="checkbox" checked={showLine} onChange={(e) => setShowLine(e.target.checked)} />
                  <span className="slider"></span>
                </label>
              </label>
            </div>

            <div style={{marginTop: 'auto', display: 'flex', flexDirection: 'column', gap: '10px', paddingTop: '20px'}}>
              <button 
                className={`btn ${isRunning ? 'btn-danger' : ''}`} 
                onClick={togglePipeline}
                style={{width: '100%'}}
              >
                {isRunning ? (
                  <>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="4" y="4" width="16" height="16" rx="2" ry="2"/></svg>
                    Stop Stream Analysis
                  </>
                ) : (
                  <>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                    Start Stream Analysis
                  </>
                )}
              </button>
              <button className="btn btn-danger" onClick={resetStats} style={{width: '100%'}}>
                Clear Statistics
              </button>
            </div>
          </section>

          {/* Video View */}
          <section className="glass-panel video-panel">
            <h2 className="panel-title" style={{width: '100%'}}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M23 7a2 2 0 0 0-2.45-1.45L16 7V5a2 2 0 0 0-2-2H2a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2l4.55 1.45A2 2 0 0 0 23 17V7z"/></svg>
              Live Monitor View
            </h2>

            <div className="screen-container">
              <video 
                ref={videoRef}
                className="video-element"
                playsInline
                muted
                style={{display: sourceType !== 'none' ? 'block' : 'none'}}
              />
              <canvas 
                ref={overlayCanvasRef}
                className="canvas-overlay"
                width={640}
                height={480}
                onMouseDown={handleMouseDown}
                onMouseMove={handleMouseMove}
                onMouseUp={handleMouseUp}
                style={{display: sourceType !== 'none' ? 'block' : 'none'}}
              />

              {sourceType === 'none' && (
                <div className="screen-placeholder">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M23 7a2 2 0 0 0-2.45-1.45L16 7V5a2 2 0 0 0-2-2H2a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2l4.55 1.45A2 2 0 0 0 23 17V7z"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
                  <div style={{fontSize: '15px', fontWeight: 500}}>No video source connected</div>
                  <div style={{fontSize: '12px'}}>Connect webcam or upload video in the left panel to begin.</div>
                </div>
              )}
            </div>

            <div style={{display: 'flex', gap: '20px', width: '100%', justifyContent: 'center', marginTop: '14px', fontSize: '13px', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)'}}>
              <div>Active Tracks: <span style={{color: 'var(--accent-cyan)'}}>{activeTracksCount}</span></div>
              <div>Processing speed: <span style={{color: 'var(--accent-cyan)'}}>{isRunning ? `${fps} FPS` : '0 FPS'}</span></div>
              {!isRunning && sourceType !== 'none' && showLine && (
                <div style={{color: '#ffc107'}}>Interactive Mode: Drag mouse on video view to redraw Virtual Line.</div>
              )}
            </div>

            <div className="counters-row">
              <div className={`counter-card entry ${animateEntry ? 'counter-inc-trigger' : ''}`}>
                <div className="counter-title">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" style={{marginRight: '6px', verticalAlign: 'middle'}}><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/><line x1="18" y1="21" x2="6" y2="21"/><path d="M6 21H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h2"/></svg>
                  Library Entries
                </div>
                <div className="counter-value">{entriesCount}</div>
              </div>
              
              <div className={`counter-card exit ${animateExit ? 'counter-inc-trigger' : ''}`}>
                <div className="counter-title">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" style={{marginRight: '6px', verticalAlign: 'middle'}}><polyline points="9 21 3 21 3 15"/><line x1="14" y1="10" x2="3" y2="21"/><line x1="6" y1="3" x2="18" y2="3"/><path d="M18 3h2a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/></svg>
                  Library Exits
                </div>
                <div className="counter-value">{exitsCount}</div>
              </div>
            </div>
          </section>

          {/* Activity Stream */}
          <section className="glass-panel">
            <h2 className="panel-title">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
              Activity Stream
            </h2>
            
            <div className="log-container">
              {logs.length === 0 ? (
                <div className="log-empty">No activity recorded yet. Start analysis to monitor gates.</div>
              ) : (
                logs.map((item) => (
                  <div key={item.id} className={`log-entry ${item.type}`}>
                    <span className="log-time">[{item.time}]</span>
                    <span className="log-text">{item.text}</span>
                  </div>
                ))
              )}
            </div>
          </section>
        </main>
      )}

      {/* REGISTRY TAB */}
      {activeTab === 'registry' && (
        <main style={{display: 'flex', flexDirection: 'column', gap: '20px', width: '100%', flexGrow: 1}}>
          {/* Enroll Form */}
          <section className="glass-panel">
            <h2 className="panel-title" style={{color: 'var(--accent-cyan)'}}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><line x1="19" y1="8" x2="19" y2="14"/><line x1="22" y1="11" x2="16" y2="11"/></svg>
              Register Enrolled Member
            </h2>

            <form onSubmit={handleRegister} className="form-card">
              <div className="form-grid">
                <div className="control-group" style={{marginBottom: 0}}>
                  <span className="control-label">Full Name</span>
                  <input type="text" className="text-input" placeholder="e.g. Nguyen Van A" value={regName} onChange={(e) => setRegName(e.target.value)} />
                </div>
                <div className="control-group" style={{marginBottom: 0}}>
                  <span className="control-label">Member Code</span>
                  <input type="text" className="text-input" placeholder="e.g. SV123456" value={regCode} onChange={(e) => setRegCode(e.target.value)} />
                </div>
                <div className="control-group" style={{marginBottom: 0}}>
                  <span className="control-label">Role</span>
                  <select className="select-input" value={regRole} onChange={(e) => setRegRole(e.target.value)}>
                    <option value="STUDENT">Student</option>
                    <option value="FACULTY">Faculty</option>
                    <option value="STAFF">Library Staff</option>
                    <option value="GUEST">Guest</option>
                  </select>
                </div>
                <div className="control-group" style={{marginBottom: 0}}>
                  <span className="control-label">Status</span>
                  <select className="select-input" value={regStatus} onChange={(e) => setRegStatus(e.target.value)}>
                    <option value="ACTIVE">Active</option>
                    <option value="INACTIVE">Inactive</option>
                  </select>
                </div>
              </div>

              <div className="form-grid" style={{alignItems: 'end'}}>
                <div className="control-group" style={{marginBottom: 0}}>
                  <span className="control-label">Portrait Image (Single Face Portrait)</span>
                  <input type="file" accept="image/*" className="select-input" style={{padding: '7px 14px'}} onChange={(e) => setRegPhoto(e.target.files?.[0] || null)} />
                </div>
                <button type="submit" className="btn" style={{height: '42px'}}>
                  Enroll Member
                </button>
              </div>
            </form>
          </section>

          {/* Members Table */}
          <section className="glass-panel" style={{flexGrow: 1}}>
            <h2 className="panel-title">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
              Registered Library Members
            </h2>

            <div className="table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Full Name</th>
                    <th>Member Code</th>
                    <th>Role</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {persons.length === 0 ? (
                    <tr>
                      <td colSpan={6} style={{textAlign: 'center', color: 'var(--text-muted)', padding: '30px'}}>
                        No members registered. Use the form above to add a member.
                      </td>
                    </tr>
                  ) : (
                    persons.map(p => (
                      <tr key={p.id}>
                        <td style={{fontFamily: 'var(--font-mono)'}}>{p.id}</td>
                        <td style={{fontWeight: 600}}>{p.full_name}</td>
                        <td style={{fontFamily: 'var(--font-mono)'}}>{p.member_code}</td>
                        <td>{p.role}</td>
                        <td>
                          <span className={`badge ${p.status === 'ACTIVE' ? 'success' : 'danger'}`}>
                            {p.status}
                          </span>
                        </td>
                        <td>
                          <button className="btn btn-danger" style={{padding: '4px 10px', fontSize: '11px'}} onClick={() => handleDeletePerson(p.id)}>
                            Delete
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </section>
        </main>
      )}

      {/* SESSIONS TAB */}
      {activeTab === 'history' && (
        <main style={{display: 'flex', flexDirection: 'column', gap: '20px', width: '100%', flexGrow: 1}}>
          <section className="glass-panel" style={{flexGrow: 1}}>
            <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-color)', paddingBottom: '8px', marginBottom: '20px', flexWrap: 'wrap', gap: '12px'}}>
              <h2 className="panel-title" style={{marginBottom: 0, borderBottom: 'none', paddingBottom: 0}}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
                Visit Session Log Book
              </h2>
              <div style={{display: 'flex', alignItems: 'center', gap: '10px'}}>
                <input
                  type="date"
                  className="text-input"
                  value={filterDate}
                  onChange={(e) => setFilterDate(e.target.value)}
                  style={{width: '160px', fontSize: '13px', padding: '6px 10px'}}
                />
                <button className="btn" onClick={loadFilteredSessions} style={{padding: '6px 14px', fontSize: '12px'}}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{marginRight: '4px'}}><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/></svg>
                  Filter
                </button>
                <button className="btn" onClick={exportToCSV} style={{padding: '6px 14px', fontSize: '12px'}}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{marginRight: '4px'}}><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                  Export CSV
                </button>
              </div>
            </div>

            <div className="table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Session ID</th>
                    <th>Member Name</th>
                    <th>Member Code</th>
                    <th>Entry Time</th>
                    <th>Exit Time</th>
                    <th>Duration</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {sessions.length === 0 ? (
                    <tr>
                      <td colSpan={7} style={{textAlign: 'center', color: 'var(--text-muted)', padding: '30px'}}>
                        No session records logged in database.
                      </td>
                    </tr>
                  ) : (
                    sessions.map(s => (
                      <tr key={s.id}>
                        <td style={{fontFamily: 'var(--font-mono)'}}>{s.id}</td>
                        <td style={{fontWeight: 600}}>{s.person_name}</td>
                        <td style={{fontFamily: 'var(--font-mono)'}}>{s.member_code || '—'}</td>
                        <td>{s.entry_at ? new Date(s.entry_at).toLocaleString() : '—'}</td>
                        <td>{s.exit_at ? new Date(s.exit_at).toLocaleString() : '—'}</td>
                        <td style={{fontFamily: 'var(--font-mono)'}}>
                          {s.duration_seconds !== null ? `${s.duration_seconds}s` : '—'}
                        </td>
                        <td>
                          <span className={`badge ${s.status === 'ACTIVE' ? 'warning' : 'success'}`}>
                            {s.status}
                          </span>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </section>
        </main>
      )}

      {/* ANALYTICS TAB */}
      {activeTab === 'analytics' && (
        <main style={{display: 'flex', flexDirection: 'column', gap: '20px', width: '100%', flexGrow: 1}}>
          {/* Stats Analytics Panel */}
          <div className="stats-cards-grid" style={{gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))'}}>
            <div className="glass-panel" style={{padding: '16px 20px'}}>
              <div style={{fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 600}}>Total Entries Today</div>
              <div style={{fontSize: '32px', fontWeight: 700, color: 'var(--accent-green)', marginTop: '8px'}}>{occupancy.total_entries_today}</div>
            </div>
            <div className="glass-panel" style={{padding: '16px 20px'}}>
              <div style={{fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 600}}>Total Exits Today</div>
              <div style={{fontSize: '32px', fontWeight: 700, color: 'var(--accent-pink)', marginTop: '8px'}}>{occupancy.total_exits_today}</div>
            </div>
            <div className="glass-panel" style={{padding: '16px 20px'}}>
              <div style={{fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 600}}>Current Occupancy</div>
              <div style={{fontSize: '32px', fontWeight: 700, color: 'var(--accent-cyan)', marginTop: '8px'}}>{occupancy.current_occupancy}</div>
            </div>
            <div className="glass-panel" style={{padding: '16px 20px'}}>
              <div style={{fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 600}}>Known Visitors</div>
              <div style={{fontSize: '32px', fontWeight: 700, color: '#7dd3fc', marginTop: '8px'}}>{occupancy.known_visitors_today}</div>
            </div>
            <div className="glass-panel" style={{padding: '16px 20px'}}>
              <div style={{fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 600}}>Unknown Visitors</div>
              <div style={{fontSize: '32px', fontWeight: 700, color: '#fbbf24', marginTop: '8px'}}>{occupancy.unknown_visitors_today}</div>
            </div>
            <div className="glass-panel" style={{padding: '16px 20px'}}>
              <div style={{fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 600}}>Total Sessions</div>
              <div style={{fontSize: '32px', fontWeight: 700, color: '#c4b5fd', marginTop: '8px'}}>{occupancy.total_sessions_today}</div>
            </div>
          </div>

          {/* Hourly Traffic Chart */}
          <section className="glass-panel chart-card" style={{flexGrow: 1}}>
            <h2 className="panel-title">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
              Hourly Peak-Traffic Volume (Today)
            </h2>

            <div className="hourly-chart">
              {hourlyStats.filter(s => s.entry > 0 || s.exit > 0).length === 0 ? (
                <div style={{textAlign: 'center', padding: '40px', color: 'var(--text-muted)', fontStyle: 'italic'}}>
                  No hourly visitor traffic recorded for today yet.
                </div>
              ) : (
                hourlyStats.map(s => {
                  const entryPct = (s.entry / maxHourlyVolume) * 100;
                  const exitPct = (s.exit / maxHourlyVolume) * 100;
                  return (
                    <div key={s.hour} className="chart-row">
                      <div className="chart-hour">{s.hour.toString().padStart(2, '0')}:00</div>
                      <div className="chart-bars-container">
                        {s.entry > 0 && (
                          <div className="bar-wrapper">
                            <div className="bar-fill entry" style={{width: `${entryPct}%`}}></div>
                            <span className="bar-val">{s.entry} entries</span>
                          </div>
                        )}
                        {s.exit > 0 && (
                          <div className="bar-wrapper">
                            <div className="bar-fill exit" style={{width: `${exitPct}%`}}></div>
                            <span className="bar-val">{s.exit} exits</span>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </section>
        </main>
      )}
    </>
  );
}

export default App;
