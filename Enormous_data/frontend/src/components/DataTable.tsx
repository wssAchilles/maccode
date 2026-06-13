import { useMemo } from 'react';
import { displayValue } from '../i18n/displayText';
import type { TableResult, TableRow } from '../types/api';

export type TableSortKey = keyof Pick<TableRow, 'event_time' | 'event_type' | 'product_id' | 'category_code' | 'brand' | 'price' | 'user_id'>;
export type TableSortDirection = 'asc' | 'desc';

type DataTableProps = {
  data: TableResult | null;
  emptyText?: string;
  isLoading?: boolean;
  loadingText?: string;
  onInspectRow?: (row: TableRow) => void;
  onSort?: (key: TableSortKey) => void;
  sortDirection?: TableSortDirection;
  sortKey?: TableSortKey;
};

const columns: Array<{ key: TableSortKey; label: string }> = [
  { key: 'event_time', label: '时间' },
  { key: 'event_type', label: '行为' },
  { key: 'product_id', label: '商品 ID' },
  { key: 'category_code', label: '原始类目' },
  { key: 'brand', label: '品牌' },
  { key: 'price', label: '价格' },
  { key: 'user_id', label: '用户 ID' },
];

function compareValue(a: TableRow, b: TableRow, key: TableSortKey) {
  const left = a[key] ?? '';
  const right = b[key] ?? '';
  if (typeof left === 'number' && typeof right === 'number') {
    return left - right;
  }
  return String(left).localeCompare(String(right), 'zh-CN', { numeric: true });
}

export function DataTable({
  data,
  emptyText = '暂无匹配的行为记录',
  isLoading = false,
  loadingText = '正在加载行为记录',
  onInspectRow,
  onSort,
  sortDirection = 'asc',
  sortKey = 'event_time',
}: DataTableProps) {
  const rows = data?.rows ?? [];
  const sortedRows = useMemo(
    () => [...rows].sort((a, b) => (sortDirection === 'asc' ? compareValue(a, b, sortKey) : compareValue(b, a, sortKey))),
    [rows, sortDirection, sortKey],
  );

  return (
    <section className="data-panel table-panel">
      <div className="panel-title">
        <div>
          <h2>行为明细</h2>
          <p>分页查看原始事件记录，支持过滤、排序、行级查看和导出当前页。</p>
        </div>
      </div>
      <div className="table-scroll" aria-label="行为明细滚动区域">
        <table aria-label="行为明细" className="data-table">
          <thead>
            <tr>
              {columns.map((column) => (
                <th
                  aria-sort={sortKey === column.key ? (sortDirection === 'asc' ? 'ascending' : 'descending') : 'none'}
                  className={column.key === 'event_time' ? 'sticky-column' : undefined}
                  key={column.key}
                >
                  <button className="table-sort-button" type="button" onClick={() => onSort?.(column.key)}>
                    {column.label}
                    <span aria-hidden="true">{sortKey === column.key ? (sortDirection === 'asc' ? '↑' : '↓') : '↕'}</span>
                  </button>
                </th>
              ))}
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan={8} className="empty-cell">{loadingText}</td>
              </tr>
            ) : null}
            {!isLoading && sortedRows.length === 0 && (
              <tr>
                <td colSpan={8} className="empty-cell">{emptyText}</td>
              </tr>
            )}
            {!isLoading && sortedRows.map((row, index) => (
              <tr key={`${row.event_time}-${row.product_id}-${index}`}>
                <td className="sticky-column">{row.event_time}</td>
                <td><span className={`event-chip event-${row.event_type}`}>{displayValue(row.event_type, 'eventType')}</span></td>
                <td>{row.product_id}</td>
                <td>{displayValue(row.category_code)}</td>
                <td>{displayValue(row.brand)}</td>
                <td>{row.price}</td>
                <td>{row.user_id}</td>
                <td>
                  <button className="table-row-action" type="button" onClick={() => onInspectRow?.(row)}>
                    查看
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
