import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';
import {
  ShieldCheck, Users, Scroll, Clock, UserPlus, MagnifyingGlass,
  Hash, Tag, CalendarBlank, CaretLeft, CaretRight, Trash,
  Database, ArrowClockwise, ArrowLeft, Warning,
} from '@phosphor-icons/react';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../hooks/useToast';
import { SkeletonRows } from './Skeleton';

const ICON = { size: 16, weight: 'regular' as const };
const ICON_SM = { size: 14, weight: 'regular' as const };

interface UserItem {
  id: number; username: string; role: string; status: string;
}

interface AuditEntry {
  id: number; action: string; entity_type: string; entity_id: number | null;
  actor: string | null; details: Record<string, unknown> | null;
  ip_address: string | null; created_at: string | null;
}

interface RetentionConfig {
  retention: {
    unknown_expire_hours: number;
    session_timeout_hours: number;
  };
  retention_cleanup_interval_seconds: number;
  audit_log_enabled: boolean;
}

type SubTab = 'users' | 'audit' | 'retention';

const SUB_TABS: { id: SubTab; label: string; Icon: typeof Users }[] = [
  { id: 'users', label: 'Người dùng', Icon: Users },
  { id: 'audit', label: 'Nhật ký', Icon: Scroll },
  { id: 'retention', label: 'Lưu trữ', Icon: Database },
];

const USER_ROLE_LABELS: Record<string, string> = {
  ADMIN: 'Quản trị',
  LIBRARIAN: 'Thủ thư',
};

const USER_STATUS_LABELS: Record<string, string> = {
  ACTIVE: 'Hoạt động',
  INACTIVE: 'Vô hiệu',
};

const badgeVariant: Record<string, string> = {
  ADMIN: 'badge-admin',
  LIBRARIAN: 'badge-librarian',
};

const panelMotion = (reduce: boolean | null) =>
  reduce
    ? { initial: false as const, animate: { opacity: 1 }, exit: { opacity: 1 } }
    : {
        initial: { opacity: 0, y: 8 },
        animate: { opacity: 1, y: 0 },
        exit: { opacity: 0, y: -6 },
        transition: { duration: 0.22, ease: [0.16, 1, 0.3, 1] as const },
      };

interface AdminPageProps {
  onBack?: () => void;
}

export function AdminPage({ onBack }: AdminPageProps) {
  const { apiFetch, isAdmin } = useAuth();
  const { show: showToast } = useToast();
  const reduceMotion = useReducedMotion();
  const visibleTabs = SUB_TABS.filter((t) => t.id !== 'users' || isAdmin);
  const [subTab, setSubTab] = useState<SubTab>('users');

  const [users, setUsers] = useState<UserItem[]>([]);
  const [usersLoading, setUsersLoading] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [uName, setUName] = useState('');
  const [uPass, setUPass] = useState('');
  const [uRole, setURole] = useState<'ADMIN' | 'LIBRARIAN'>('LIBRARIAN');

  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [auditTotal, setAuditTotal] = useState(0);
  const [auditLoading, setAuditLoading] = useState(false);
  const [auditPage, setAuditPage] = useState(0);
  const [filterAction, setFilterAction] = useState('');
  const [filterEntity, setFilterEntity] = useState('');

  const [config, setConfig] = useState<RetentionConfig | null>(null);
  const [cfgLoading, setCfgLoading] = useState(false);
  const [cleanupResult, setCleanupResult] = useState<Record<string, unknown> | null>(null);
  const [cleanupLoading, setCleanupLoading] = useState(false);
  const [confirmCleanup, setConfirmCleanup] = useState(false);

  const loadUsers = useCallback(async () => {
    setUsersLoading(true);
    try {
      const res = await apiFetch('/api/auth/users');
      if (res.ok) setUsers((await res.json()).items ?? []);
      else showToast('Không tải được danh sách người dùng.', 'error');
    } catch { showToast('Lỗi kết nối.', 'error'); }
    finally { setUsersLoading(false); }
  }, [apiFetch, showToast]);

  const createUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uName.trim() || !uPass) { showToast('Nhập đầy đủ thông tin.', 'error'); return; }
    try {
      const res = await apiFetch('/api/auth/register', {
        method: 'POST',
        body: JSON.stringify({ username: uName.trim(), password: uPass, role: uRole }),
      });
      if (res.ok) {
        showToast('Đã tạo người dùng.', 'success');
        setShowForm(false); setUName(''); setUPass(''); setURole('LIBRARIAN');
        loadUsers();
      } else {
        const err = await res.json().catch(() => ({}));
        showToast(err.detail || 'Thất bại.', 'error');
      }
    } catch { showToast('Lỗi kết nối.', 'error'); }
  };

  const loadAudit = useCallback(async () => {
    setAuditLoading(true);
    try {
      const p = new URLSearchParams({ skip: String(auditPage * 100), limit: '100' });
      if (filterAction) p.set('action', filterAction);
      if (filterEntity) p.set('entity_type', filterEntity);
      const res = await apiFetch(`/api/admin/audit-log?${p}`);
      if (res.ok) {
        const d = await res.json();
        setEntries(d.items ?? []); setAuditTotal(d.total ?? 0);
      } else showToast('Không tải được nhật ký.', 'error');
    } catch { showToast('Lỗi kết nối.', 'error'); }
    finally { setAuditLoading(false); }
  }, [apiFetch, showToast, auditPage, filterAction, filterEntity]);

  const loadConfig = useCallback(async () => {
    setCfgLoading(true);
    try {
      const res = await apiFetch('/api/admin/retention/config');
      if (res.ok) setConfig(await res.json());
    } catch { showToast('Không tải được cấu hình.', 'error'); }
    finally { setCfgLoading(false); }
  }, [apiFetch, showToast]);

  const triggerCleanup = async () => {
    setCleanupLoading(true); setCleanupResult(null); setConfirmCleanup(false);
    try {
      const res = await apiFetch('/api/admin/retention/run', { method: 'POST' });
      if (res.ok) { setCleanupResult(await res.json()); showToast('Đã dọn dẹp.', 'success'); }
      else showToast('Dọn dẹp thất bại.', 'error');
    } catch { showToast('Lỗi kết nối.', 'error'); }
    finally { setCleanupLoading(false); }
  };

  const toggleUserRole = async (u: UserItem) => {
    const newRole = u.role === 'ADMIN' ? 'LIBRARIAN' : 'ADMIN';
    try {
      const res = await apiFetch(`/api/auth/users/${u.id}`, {
        method: 'PUT',
        body: JSON.stringify({ role: newRole }),
      });
      if (res.ok) { showToast(`Đã đổi vai trò ${u.username} thành ${USER_ROLE_LABELS[newRole]}.`, 'success'); loadUsers(); }
      else { const e = await res.json().catch(() => ({})); showToast(e.detail || 'Thất bại.', 'error'); }
    } catch { showToast('Lỗi kết nối.', 'error'); }
  };

  const toggleUserStatus = async (u: UserItem) => {
    const newStatus = u.status === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE';
    try {
      const res = await apiFetch(`/api/auth/users/${u.id}`, {
        method: 'PUT',
        body: JSON.stringify({ status: newStatus }),
      });
      if (res.ok) { showToast(`Đã ${newStatus === 'ACTIVE' ? 'kích hoạt' : 'vô hiệu hoá'} ${u.username}.`, 'success'); loadUsers(); }
      else { const e = await res.json().catch(() => ({})); showToast(e.detail || 'Thất bại.', 'error'); }
    } catch { showToast('Lỗi kết nối.', 'error'); }
  };

  useEffect(() => { if (subTab === 'users') loadUsers(); }, [subTab, loadUsers]);
  useEffect(() => { if (subTab === 'audit') loadAudit(); }, [subTab, loadAudit]);
  useEffect(() => { if (subTab === 'retention') loadConfig(); }, [subTab, loadConfig]);

  const totalPages = Math.ceil(auditTotal / 100);
  const motionProps = panelMotion(reduceMotion);

  return (
    <motion.div
      className="page-stack page-view admin-page"
      initial={reduceMotion ? false : { opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
    >
      <div className="admin-header">
        <div className="admin-header-left">
          {onBack && (
            <button
              type="button"
              className="admin-back-btn"
              onClick={onBack}
              data-testid="admin-back"
              aria-label="Quay lại trang trước"
            >
              <ArrowLeft {...ICON_SM} />
              <span>Quay lại</span>
            </button>
          )}
          <div className="admin-header-title-block">
            <ShieldCheck size={20} weight="fill" className="admin-header-icon" />
            <div>
              <h2 className="admin-header-title">Quản trị hệ thống</h2>
              <p className="admin-header-desc">Tài khoản, nhật ký và vòng đời dữ liệu</p>
            </div>
          </div>
        </div>
      </div>

      <nav className="admin-segment" role="tablist" aria-label="Phần quản trị">
        {visibleTabs.map(({ id, label, Icon }) => (
          <button
            key={id}
            role="tab"
            type="button"
            aria-selected={subTab === id}
            className={`admin-segment-btn ${subTab === id ? 'active' : ''}`}
            onClick={() => { setSubTab(id); setConfirmCleanup(false); }}
          >
            <Icon {...ICON_SM} />
            {label}
          </button>
        ))}
      </nav>

      <AnimatePresence mode="wait">
        {subTab === 'users' && (
          <motion.section key="users" className="admin-section" role="tabpanel" {...motionProps}>
            <div className="admin-section-hd">
              <h3><Users {...ICON} /> Người dùng</h3>
              <button type="button" className="btn btn-primary btn-sm" onClick={() => setShowForm(!showForm)}>
                <UserPlus {...ICON_SM} />
                {showForm ? 'Huỷ' : 'Thêm người dùng'}
              </button>
            </div>

            <AnimatePresence>
              {showForm && (
                <motion.form
                  className="admin-create-form"
                  onSubmit={createUser}
                  initial={reduceMotion ? false : { height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={reduceMotion ? undefined : { height: 0, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  <div className="admin-form-grid">
                    <label className="admin-field">
                      <span className="admin-field-label">Tên đăng nhập</span>
                      <input
                        className="text-input"
                        value={uName}
                        onChange={(e) => setUName(e.target.value)}
                        autoFocus
                        autoComplete="off"
                      />
                    </label>
                    <label className="admin-field">
                      <span className="admin-field-label">Mật khẩu</span>
                      <input
                        className="text-input"
                        type="password"
                        value={uPass}
                        onChange={(e) => setUPass(e.target.value)}
                        autoComplete="new-password"
                      />
                    </label>
                    <label className="admin-field">
                      <span className="admin-field-label">Vai trò</span>
                      <select
                        className="select-input"
                        value={uRole}
                        onChange={(e) => setURole(e.target.value as 'ADMIN' | 'LIBRARIAN')}
                      >
                        <option value="LIBRARIAN">Thủ thư</option>
                        <option value="ADMIN">Quản trị</option>
                      </select>
                    </label>
                    <div className="admin-field admin-field--action">
                      <button type="submit" className="btn btn-primary btn-sm">Tạo tài khoản</button>
                    </div>
                  </div>
                </motion.form>
              )}
            </AnimatePresence>

            <div className="admin-table-wrap">
              {usersLoading ? (
                <div className="admin-skeleton" aria-busy="true" aria-label="Đang tải người dùng">
                  <SkeletonRows rows={4} />
                </div>
              ) : users.length === 0 ? (
                <div className="admin-empty">
                  <Users size={28} weight="duotone" />
                  <p>Chưa có người dùng</p>
                  <span>Thêm tài khoản để cấp quyền truy cập dashboard.</span>
                </div>
              ) : (
                <table className="admin-table">
                  <thead>
                    <tr>
                      <th><Hash {...ICON_SM} /> ID</th>
                      <th>Tên đăng nhập</th>
                      <th><Tag {...ICON_SM} /> Vai trò</th>
                      <th>Trạng thái</th>
                      {isAdmin && <th>Thao tác</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {users.map((u) => (
                      <tr key={u.id}>
                        <td className="mono">{u.id}</td>
                        <td className="admin-user-name">{u.username}</td>
                        <td><span className={`badge ${badgeVariant[u.role] || ''}`}>{USER_ROLE_LABELS[u.role] || u.role}</span></td>
                        <td>
                          <span className={`status-dot ${u.status === 'ACTIVE' ? 'active' : ''}`} />
                          {USER_STATUS_LABELS[u.status] || u.status}
                        </td>
                        {isAdmin && (
                          <td className="admin-actions">
                            <button type="button" className="btn btn-sm" onClick={() => toggleUserRole(u)} title="Đổi vai trò">
                              <Tag {...ICON_SM} />
                            </button>
                            <button type="button" className={`btn btn-sm ${u.status === 'ACTIVE' ? 'btn-danger' : 'btn-primary'}`} onClick={() => toggleUserStatus(u)} title={u.status === 'ACTIVE' ? 'Vô hiệu hoá' : 'Kích hoạt'}>
                              {u.status === 'ACTIVE' ? <Warning {...ICON_SM} /> : <ShieldCheck {...ICON_SM} />}
                            </button>
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </motion.section>
        )}

        {subTab === 'audit' && (
          <motion.section key="audit" className="admin-section" role="tabpanel" {...motionProps}>
            <div className="admin-section-hd">
              <h3><Scroll {...ICON} /> Nhật ký hoạt động</h3>
              <div className="admin-filter-group">
                <div className="admin-filter-input">
                  <MagnifyingGlass size={12} />
                  <input
                    className="text-input text-input--icon"
                    placeholder="Lọc action"
                    aria-label="Lọc theo action"
                    value={filterAction}
                    onChange={(e) => { setFilterAction(e.target.value); setAuditPage(0); }}
                  />
                </div>
                <div className="admin-filter-input">
                  <MagnifyingGlass size={12} />
                  <input
                    className="text-input text-input--icon"
                    placeholder="Lọc entity"
                    aria-label="Lọc theo entity"
                    value={filterEntity}
                    onChange={(e) => { setFilterEntity(e.target.value); setAuditPage(0); }}
                  />
                </div>
                {(filterAction || filterEntity) && (
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    title="Xoá lọc"
                    onClick={() => { setFilterAction(''); setFilterEntity(''); setAuditPage(0); }}
                  >
                    <Trash {...ICON_SM} />
                  </button>
                )}
              </div>
            </div>

            <div className="admin-table-wrap">
              {auditLoading ? (
                <div className="admin-skeleton" aria-busy="true" aria-label="Đang tải nhật ký">
                  <SkeletonRows rows={6} />
                </div>
              ) : entries.length === 0 ? (
                <div className="admin-empty">
                  <Scroll size={28} weight="duotone" />
                  <p>Không có nhật ký</p>
                  <span>Các thao tác hệ thống sẽ xuất hiện tại đây.</span>
                </div>
              ) : (
                <table className="admin-table admin-table--compact">
                  <thead>
                    <tr>
                      <th><CalendarBlank {...ICON_SM} /> Thời gian</th>
                      <th>Hành động</th>
                      <th>Đối tượng</th>
                      <th>ID</th>
                      <th>Người thực hiện</th>
                      <th>IP</th>
                      <th>Chi tiết</th>
                    </tr>
                  </thead>
                  <tbody>
                    {entries.map((e) => {
                      const detail = e.details ? JSON.stringify(e.details) : '';
                      return (
                        <tr key={e.id}>
                          <td className="mono muted">
                            {e.created_at ? new Date(e.created_at).toLocaleString('vi-VN') : '-'}
                          </td>
                          <td><span className="badge badge-action">{e.action}</span></td>
                          <td className="muted">{e.entity_type}</td>
                          <td className="mono muted">{e.entity_id ?? '-'}</td>
                          <td>{e.actor ?? '-'}</td>
                          <td className="mono muted">{e.ip_address ?? '-'}</td>
                          <td className="cell-details" title={detail || undefined}>
                            {detail
                              ? detail.slice(0, 60) + (detail.length > 60 ? '…' : '')
                              : '-'}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>

            {totalPages > 1 && (
              <div className="admin-pagination">
                <button
                  type="button"
                  className="btn btn-sm"
                  disabled={auditPage === 0}
                  onClick={() => setAuditPage((p) => p - 1)}
                >
                  <CaretLeft {...ICON_SM} /> Trước
                </button>
                <span className="admin-page-info">Trang {auditPage + 1} / {totalPages}</span>
                <button
                  type="button"
                  className="btn btn-sm"
                  disabled={auditPage >= totalPages - 1}
                  onClick={() => setAuditPage((p) => p + 1)}
                >
                  Sau <CaretRight {...ICON_SM} />
                </button>
              </div>
            )}
          </motion.section>
        )}

        {subTab === 'retention' && (
          <motion.section key="retention" className="admin-section" role="tabpanel" {...motionProps}>
            <div className="admin-section-hd">
              <h3><Database {...ICON} /> Cấu hình lưu trữ</h3>
            </div>

            {cfgLoading ? (
              <div className="admin-skeleton" aria-busy="true" aria-label="Đang tải cấu hình">
                <SkeletonRows rows={3} />
              </div>
            ) : config ? (
              <div className="retention-grid">
                {[
                  { label: 'Hết hạn danh tính lạ', value: `${config.retention.unknown_expire_hours} giờ`, icon: Clock },
                  { label: 'Thời gian gia hạn', value: `${config.retention.session_timeout_hours} giờ`, icon: Clock },
                  { label: 'Chu kỳ dọn dẹp', value: `${config.retention_cleanup_interval_seconds}s`, icon: ArrowClockwise },
                  { label: 'Ghi nhật ký', value: config.audit_log_enabled ? 'Bật' : 'Tắt', icon: Scroll },
                ].map(({ label, value, icon: Icon }) => (
                  <div key={label} className="retention-card">
                    <Icon className="retention-card-icon" {...ICON} />
                    <span className="retention-card-label">{label}</span>
                    <span className="retention-card-value">{value}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="admin-empty">
                <Database size={28} weight="duotone" />
                <p>Không tải được cấu hình</p>
              </div>
            )}

            <AnimatePresence>
              {cleanupResult && (
                <motion.div
                  className="cleanup-result"
                  initial={reduceMotion ? false : { opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={reduceMotion ? undefined : { opacity: 0, height: 0 }}
                >
                  <h4>Kết quả dọn dẹp</h4>
                  <div className="cleanup-stats">
                    <div className="cleanup-stat">
                      <span className="cleanup-stat-label">Đã đóng phiên</span>
                      <strong>{String(cleanupResult.closed_sessions ?? '?')}</strong>
                    </div>
                    <div className="cleanup-stat">
                      <span className="cleanup-stat-label">Đã hết hạn danh tính</span>
                      <strong>{String(cleanupResult.expired_identities ?? '?')}</strong>
                    </div>
                    <div className="cleanup-stat">
                      <span className="cleanup-stat-label">Đã xoá embeddings</span>
                      <strong>{String(cleanupResult.purged_embeddings ?? '?')}</strong>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            <AnimatePresence mode="wait">
              {confirmCleanup ? (
                <motion.div
                  key="cleanup-confirm"
                  className="admin-confirm-bar"
                  initial={reduceMotion ? false : { opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={reduceMotion ? undefined : { opacity: 0, y: 4 }}
                  role="alertdialog"
                  aria-labelledby="cleanup-confirm-title"
                >
                  <div className="admin-confirm-copy">
                    <Warning size={18} weight="fill" className="admin-confirm-icon" />
                    <div>
                      <p id="cleanup-confirm-title">Chạy dọn dẹp ngay?</p>
                      <span>Thao tác sẽ đóng phiên hết hạn và xoá embedding theo cấu hình hiện tại.</span>
                    </div>
                  </div>
                  <div className="admin-confirm-actions">
                    <button type="button" className="btn btn-ghost btn-sm" onClick={() => setConfirmCleanup(false)}>
                      Huỷ
                    </button>
                    <button
                      type="button"
                      className="btn btn-primary btn-sm"
                      disabled={cleanupLoading}
                      onClick={triggerCleanup}
                      data-testid="admin-cleanup-confirm"
                    >
                      {cleanupLoading ? 'Đang dọn…' : 'Xác nhận dọn'}
                    </button>
                  </div>
                </motion.div>
              ) : (
                <motion.button
                  key="cleanup-trigger"
                  type="button"
                  className="btn btn-primary"
                  disabled={cleanupLoading || !config}
                  onClick={() => setConfirmCleanup(true)}
                  data-testid="admin-cleanup"
                  initial={false}
                >
                  {cleanupLoading ? 'Đang dọn…' : 'Dọn dẹp ngay'}
                </motion.button>
              )}
            </AnimatePresence>
          </motion.section>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
