// Standard container used for every section of every page.
// `index` sets the order of the entrance animation.
export default function Panel({ title, subtitle, actions, flush = false, index = 0, className = '', children }) {
  return (
    <section className={`panel reveal ${className}`} style={{ '--i': index }}>
      {(title || actions) && (
        <div className="panel-header">
          <div>
            {title && <h3 className="panel-title">{title}</h3>}
            {subtitle && <p className="panel-subtitle">{subtitle}</p>}
          </div>
          {actions && <div className="panel-actions">{actions}</div>}
        </div>
      )}
      <div className={`panel-body ${flush ? 'flush' : ''}`}>{children}</div>
    </section>
  );
}
