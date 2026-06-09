import type { TableResult } from '../types/api';

type DataTableProps = {
  data: TableResult | null;
};

export function DataTable({ data }: DataTableProps) {
  const rows = data?.rows ?? [];
  return (
    <section className="data-panel table-panel">
      <div className="panel-title">
        <div>
          <h2>行为明细</h2>
          <p>分页查看原始事件记录，支持按行为类型过滤。</p>
        </div>
      </div>
      <div className="table-scroll" aria-label="行为明细滚动区域">
        <table aria-label="行为明细">
          <thead>
            <tr>
              <th>时间</th>
              <th>行为</th>
              <th>商品</th>
              <th>类目</th>
              <th>品牌</th>
              <th>价格</th>
              <th>用户</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr>
                <td colSpan={7} className="empty-cell">暂无匹配的行为记录</td>
              </tr>
            )}
            {rows.map((row, index) => (
              <tr key={`${row.event_time}-${row.product_id}-${index}`}>
                <td>{row.event_time}</td>
                <td><span className={`event-chip event-${row.event_type}`}>{row.event_type}</span></td>
                <td>{row.product_id}</td>
                <td>{row.category_code || 'unknown'}</td>
                <td>{row.brand || 'unknown'}</td>
                <td>{row.price}</td>
                <td>{row.user_id}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
