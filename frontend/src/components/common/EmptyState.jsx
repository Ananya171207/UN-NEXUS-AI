export default function EmptyState({ icon: Icon, title, children }) {
  return (
    <div className="empty-state">
      {Icon && <Icon size={26} />}
      <strong>{title}</strong>
      {children && <p>{children}</p>}
    </div>
  );
}
