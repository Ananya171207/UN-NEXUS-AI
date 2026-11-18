import { Hammer } from 'lucide-react';
import Panel from '../../components/common/Panel';
import EmptyState from '../../components/common/EmptyState';
import DataBadge from '../../components/common/DataBadge';

// Temporary page for modules that are built in later phases.
// Each phase replaces one of these with the real module.
export default function ComingSoon({ page }) {
  return (
    <div className="page">
      <Panel
        title={page.label}
        subtitle={page.description}
        actions={<DataBadge type="neutral">Phase {page.phase}</DataBadge>}
      >
        <EmptyState icon={Hammer} title="This module is under development">
          It will be built in Phase {page.phase} of the frontend plan.
        </EmptyState>
      </Panel>
    </div>
  );
}
