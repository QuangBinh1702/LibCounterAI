import React, { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { MagnifyingGlass, UserPlus, Users, Pencil, Warning, X, Eye, CalendarBlank, ShieldCheck } from '@phosphor-icons/react';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../hooks/useToast';
import { SkeletonRows } from './Skeleton';

const ICON = { size: 16, weight: 'regular' as const };

interface Person {
  id: number;
  full_name: string;
  member_code: string;
  role: string;
  status: string;
}

interface FaceTemplateInfo {
  id: number;
  model_name: string;
  quality_score: number;
  source_type: string;
  is_active: boolean;
  created_at: string | null;
}

interface SessionInfo {
  id: number;
  entry_at: string | null;
  exit_at: string | null;
  duration_seconds: number | null;
  status: string;
}

interface PersonDetail {
  id: number;
  full_name: string;
  member_code: string;
  role: string;
  status: string;
  created_at: string | null;
  face_templates: FaceTemplateInfo[];
  recent_sessions: SessionInfo[];
}

const ROLE_LABELS: Record<string, string> = {
  STUDENT: 'Sinh viên',
  FACULTY: 'Giảng viên',
  STAFF: 'Nhân viên',
  GUEST: 'Khách',
};

export function RegistryPage() {
  const { apiFetch } = useAuth();
  const { show: showToast } = useToast();

  const [persons, setPersons] = useState<Person[]>([]);
  const [loading, setLoading] = useState(false);
  const [regName, setRegName] = useState('');
  const [regCode, setRegCode] = useState('');
  const [regRole, setRegRole] = useState('STUDENT');
  const [regPhoto, setRegPhoto] = useState<File | null>(null);
  const [editingPerson, setEditingPerson] = useState<Person | null>(null);
  const [editName, setEditName] = useState('');
  const [editCode, setEditCode] = useState('');
  const [editRole, setEditRole] = useState('STUDENT');
  const [editStatus, setEditStatus] = useState('ACTIVE');
  const [editPhoto, setEditPhoto] = useState<File | null>(null);
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('ALL');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [personToDelete, setPersonToDelete] = useState<Person | null>(null);
  const [detailPerson, setDetailPerson] = useState<PersonDetail | null>(null);
  const editNameInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => { loadPersons(); }, []);

  const loadPersons = async () => {
    setLoading(true);
    try {
      const res = await apiFetch('/api/persons');
      if (res.ok) {
        const data = await res.json();
        setPersons(data.items || data || []);
      }
    } catch (err) {
      console.error('Failed to load persons:', err);
      showToast('Không tải được danh sách thành viên.', 'error');
    } finally {
      setLoading(false);
    }
  };

  const loadPersonDetail = async (id: number) => {
    try {
      const res = await apiFetch(`/api/persons/${id}`);
      if (res.ok) {
        setDetailPerson(await res.json());
      } else {
        showToast('Không tải được thông tin thành viên.', 'error');
      }
    } catch {
      showToast('Lỗi kết nối.', 'error');
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
    formData.append('file', regPhoto);
    try {
      const res = await apiFetch('/api/persons/register', { method: 'POST', body: formData });
      if (!res.ok) {
        const err = await res.json();
        showToast(`Đăng ký thất bại: ${err.detail || 'Lỗi không xác định'}`, 'error');
        return;
      }
      showToast('Đăng ký thành viên mới thành công.', 'success');
      setRegName('');
      setRegCode('');
      setRegRole('STUDENT');
      setRegPhoto(null);
      loadPersons();
    } catch (err) {
      showToast(`Lỗi kết nối backend: ${err}`, 'error');
    }
  };

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

  useEffect(() => {
    if (!editingPerson) return;

    const previousOverflow = document.body.style.overflow;
    document.body.classList.add('has-modal-open');
    document.body.style.overflow = 'hidden';
    editNameInputRef.current?.focus();

    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') cancelEditPerson();
    };
    window.addEventListener('keydown', closeOnEscape);

    return () => {
      document.body.classList.remove('has-modal-open');
      document.body.style.overflow = previousOverflow;
      window.removeEventListener('keydown', closeOnEscape);
    };
  }, [editingPerson]);

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
    if (editPhoto) formData.append('file', editPhoto);

    try {
      const res = await apiFetch(`/api/persons/${editingPerson.id}`, { method: 'PUT', body: formData });
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

  const handleDeletePerson = async () => {
    if (!personToDelete) return;
    try {
      const res = await apiFetch(`/api/persons/${personToDelete.id}`, { method: 'DELETE' });
      if (res.ok) {
        showToast('Đã xóa thành viên.', 'success');
        setPersonToDelete(null);
        loadPersons();
      } else {
        showToast('Xóa thành viên thất bại.', 'error');
      }
    } catch (err) {
      showToast(`Lỗi kết nối: ${err}`, 'error');
    }
  };

  const visiblePersons = persons.filter((person) => {
    const needle = search.trim().toLocaleLowerCase('vi-VN');
    const matchesSearch = !needle || person.full_name.toLocaleLowerCase('vi-VN').includes(needle) || person.member_code.toLocaleLowerCase('vi-VN').includes(needle);
    return matchesSearch && (roleFilter === 'ALL' || person.role === roleFilter) && (statusFilter === 'ALL' || person.status === statusFilter);
  });

  return (
    <div className="page-stack page-view">
      <section className="panel registry-form-panel">
        <h2 className="panel-title"><UserPlus {...ICON} /> Đăng ký thành viên</h2>
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
              <UserPlus {...ICON} /> Đăng ký
            </button>
          </div>
        </form>
      </section>

      <section className="panel panel-grow">
        <div className="registry-list-header"><h2 className="panel-title"><Users {...ICON} /> Danh sách thành viên</h2><span className="registry-count">{visiblePersons.length} / {persons.length}</span></div>
        <div className="registry-filters">
          <label className="registry-search"><MagnifyingGlass size={15} /><input className="text-input" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Tìm tên hoặc mã thẻ…" aria-label="Tìm thành viên" /></label>
          <select className="select-input" value={roleFilter} onChange={(event) => setRoleFilter(event.target.value)} aria-label="Lọc theo vai trò"><option value="ALL">Mọi vai trò</option>{Object.entries(ROLE_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select>
          <select className="select-input" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} aria-label="Lọc theo trạng thái"><option value="ALL">Mọi trạng thái</option><option value="ACTIVE">Hoạt động</option><option value="INACTIVE">Ngưng</option></select>
        </div>
        {loading ? (
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
                {visiblePersons.length === 0 ? (
                  <tr>
                    <td colSpan={6}>
                      <div className="empty-state">
                        <div className="empty-state-title">Chưa có thành viên</div>
                        Dùng form phía trên để đăng ký thành viên mới.
                      </div>
                    </td>
                  </tr>
                ) : (
                  visiblePersons.map((p) => (
                    <tr key={p.id}>
                      <td className="mono">{p.id}</td>
                      <td><span className="cell-strong person-name-link" onClick={() => loadPersonDetail(p.id)} role="button" tabIndex={0} onKeyDown={(e) => e.key === 'Enter' && loadPersonDetail(p.id)}>{p.full_name} <Eye size={12} className="person-name-icon" /></span></td>
                      <td className="mono">{p.member_code}</td>
                      <td>{ROLE_LABELS[p.role] || p.role}</td>
                      <td>
                        <span className={`badge ${p.status === 'ACTIVE' ? 'success' : 'danger'}`}>
                          {p.status === 'ACTIVE' ? 'Hoạt động' : 'Ngưng'}
                        </span>
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: '8px' }}>
                          <button type="button" className="btn btn-sm" onClick={() => startEditPerson(p)}><Pencil {...{ size: 14, weight: 'regular' }} /> Sửa</button>
                          <button type="button" className="btn btn-danger btn-sm" onClick={() => setPersonToDelete(p)}>Xóa</button>
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

      {editingPerson && createPortal(
        <div className="modal-overlay" role="presentation" onMouseDown={cancelEditPerson}>
          <div className="modal-container" role="dialog" aria-modal="true" aria-labelledby="edit-member-title" onMouseDown={(event) => event.stopPropagation()}>
            <div className="modal-header">
              <h3 id="edit-member-title" className="modal-title"><Pencil {...ICON} /> Cập nhật thành viên</h3>
              <button type="button" className="modal-close-btn" aria-label="Đóng cửa sổ cập nhật" onClick={cancelEditPerson}><X size={18} /></button>
            </div>
            <div className="modal-body">
              <form onSubmit={handleUpdatePerson} className="form-card" style={{ boxShadow: 'none', padding: 0, border: 0 }}>
                <div className="form-grid" style={{ gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>
                  <div className="control-group control-group-flush">
                    <span className="control-label">Họ và tên</span>
                    <input ref={editNameInputRef} type="text" className="text-input" placeholder="Nguyễn Văn A" value={editName} onChange={(e) => setEditName(e.target.value)} required />
                  </div>
                  <div className="control-group control-group-flush">
                    <span className="control-label">Mã thẻ</span>
                    <input type="text" className="text-input" placeholder="SV123456" value={editCode} onChange={(e) => setEditCode(e.target.value)} required />
                  </div>
                  <div className="control-group control-group-flush">
                    <span className="control-label">Vai trò</span>
                    <select className="select-input" value={editRole} onChange={(e) => setEditRole(e.target.value)}>
                      <option value="STUDENT">Sinh viên</option><option value="FACULTY">Giảng viên</option>
                      <option value="STAFF">Nhân viên thư viện</option>
                    </select>
                  </div>
                  <div className="control-group control-group-flush">
                    <span className="control-label">Trạng thái</span>
                    <select className="select-input" value={editStatus} onChange={(e) => setEditStatus(e.target.value)}>
                      <option value="ACTIVE">Hoạt động</option><option value="INACTIVE">Ngưng</option>
                    </select>
                  </div>
                </div>
                <div className="control-group" style={{ marginBottom: '20px' }}>
                  <span className="control-label">Ảnh chân dung mới (tùy chọn)</span>
                  <input type="file" accept="image/*" className="select-input" onChange={(e) => setEditPhoto(e.target.files?.[0] || null)} />
                  <span className="field-hint">Bỏ trống nếu giữ nguyên ảnh cũ · JPEG, PNG · Tối đa 10MB</span>
                </div>
                <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
                  <button type="button" className="btn btn-ghost" onClick={cancelEditPerson}>Hủy</button>
                  <button type="submit" className="btn form-submit-btn"><Pencil {...ICON} /> Lưu thay đổi</button>
                </div>
              </form>
            </div>
          </div>
        </div>,
        document.body,
      )}
      {personToDelete && createPortal(
        <div className="modal-overlay" role="presentation" onMouseDown={() => setPersonToDelete(null)}>
          <div className="confirm-dialog" role="alertdialog" aria-modal="true" aria-labelledby="delete-member-title" onMouseDown={(event) => event.stopPropagation()}>
            <Warning size={24} weight="fill" className="confirm-dialog-icon" />
            <h3 id="delete-member-title">Xóa {personToDelete.full_name}?</h3>
            <p>Thành viên và dữ liệu sinh trắc học liên quan sẽ bị xóa vĩnh viễn. Thao tác này không thể hoàn tác.</p>
            <div className="confirm-dialog-actions"><button type="button" className="btn btn-ghost" onClick={() => setPersonToDelete(null)}>Hủy</button><button type="button" className="btn btn-danger" onClick={handleDeletePerson}>Xóa thành viên</button></div>
          </div>
        </div>,
        document.body,
      )}
      {detailPerson && createPortal(
        <div className="modal-overlay" role="presentation" onMouseDown={() => setDetailPerson(null)}>
          <div className="modal-container" role="dialog" aria-modal="true" aria-labelledby="detail-member-title" onMouseDown={(event) => event.stopPropagation()}>
            <div className="modal-header">
              <h3 id="detail-member-title" className="modal-title"><Eye {...ICON} /> {detailPerson.full_name}</h3>
              <button type="button" className="modal-close-btn" aria-label="Đóng" onClick={() => setDetailPerson(null)}><X size={18} /></button>
            </div>
            <div className="modal-body">
              <div className="detail-grid">
                <div className="detail-section">
                  <h4 className="detail-section-title"><Users {...ICON} /> Thông tin</h4>
                  <div className="detail-rows">
                    <div className="detail-row"><span className="detail-label">Mã thẻ</span><span className="detail-value mono">{detailPerson.member_code}</span></div>
                    <div className="detail-row"><span className="detail-label">Vai trò</span><span className="detail-value">{ROLE_LABELS[detailPerson.role] || detailPerson.role}</span></div>
                    <div className="detail-row"><span className="detail-label">Trạng thái</span><span className={`badge ${detailPerson.status === 'ACTIVE' ? 'success' : 'danger'}`}>{detailPerson.status === 'ACTIVE' ? 'Hoạt động' : 'Ngưng'}</span></div>
                    <div className="detail-row"><span className="detail-label">Ngày tạo</span><span className="detail-value">{detailPerson.created_at ? new Date(detailPerson.created_at).toLocaleDateString('vi-VN') : '-'}</span></div>
                  </div>
                </div>
                <div className="detail-section">
                  <h4 className="detail-section-title"><ShieldCheck {...ICON} /> Khuôn mặt ({detailPerson.face_templates.length})</h4>
                  {detailPerson.face_templates.length === 0 ? (
                    <p className="detail-empty">Chưa có mẫu khuôn mặt</p>
                  ) : (
                    <div className="detail-rows">
                      {detailPerson.face_templates.map((t) => (
                        <div key={t.id} className="detail-row">
                          <span className="detail-label">{t.model_name}</span>
                          <span className="detail-value">
                            <span className={`badge ${t.is_active ? 'success' : ''}`}>{t.is_active ? 'Hoạt động' : 'Vô hiệu'}</span>
                            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{(t.quality_score * 100).toFixed(0)}%</span>
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                <div className="detail-section detail-section--full">
                  <h4 className="detail-section-title"><CalendarBlank {...ICON} /> Lịch sử ra/vào (20 gần nhất)</h4>
                  {detailPerson.recent_sessions.length === 0 ? (
                    <p className="detail-empty">Chưa có phiên ra/vào</p>
                  ) : (
                    <table className="admin-table admin-table--compact">
                      <thead>
                        <tr>
                          <th>Vào</th>
                          <th>Ra</th>
                          <th>Thời lượng</th>
                          <th>Trạng thái</th>
                        </tr>
                      </thead>
                      <tbody>
                        {detailPerson.recent_sessions.map((s) => (
                          <tr key={s.id}>
                            <td className="mono muted">{s.entry_at ? new Date(s.entry_at).toLocaleString('vi-VN') : '-'}</td>
                            <td className="mono muted">{s.exit_at ? new Date(s.exit_at).toLocaleString('vi-VN') : '-'}</td>
                            <td className="mono">{s.duration_seconds ? `${Math.floor(s.duration_seconds / 60)}p` : '-'}</td>
                            <td><span className={`badge ${s.status === 'CLOSED' ? 'success' : s.status === 'ACTIVE' ? 'warning' : ''}`}>{s.status === 'CLOSED' ? 'Đã đóng' : s.status === 'ACTIVE' ? 'Đang mở' : s.status === 'TIMEOUT' ? 'Quá hạn' : s.status}</span></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>,
        document.body,
      )}
    </div>
  );
}
