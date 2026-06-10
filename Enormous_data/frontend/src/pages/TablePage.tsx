import { useState } from 'react';
import { useTable } from '../api/hooks';
import { DataTable, type TableSortDirection, type TableSortKey } from '../components/DataTable';
import { ErrorBanner } from '../components/feedback/ErrorBanner';
import { formatNumber } from '../lib/format';
import type { TableRow } from '../types/api';

function csvCell(value: string | number | null | undefined) {
  const text = String(value ?? '');
  return `"${text.replace(/"/g, '""')}"`;
}

export function TablePage() {
  const [eventType, setEventType] = useState('');
  const [pageSize, setPageSize] = useState(10);
  const [page, setPage] = useState(1);
  const [sortKey, setSortKey] = useState<TableSortKey>('event_time');
  const [sortDirection, setSortDirection] = useState<TableSortDirection>('desc');
  const [selectedRow, setSelectedRow] = useState<TableRow | null>(null);
  const table = useTable({ page, size: pageSize, event_type: eventType });

  function onSort(key: TableSortKey) {
    if (sortKey === key) {
      setSortDirection((direction) => (direction === 'asc' ? 'desc' : 'asc'));
      return;
    }
    setSortKey(key);
    setSortDirection('asc');
  }

  function exportCurrentPage() {
    const rows = table.data?.rows ?? [];
    const header = ['event_time', 'event_type', 'product_id', 'category_code', 'brand', 'price', 'user_id'];
    const csv = [header.join(','), ...rows.map((row) => header.map((key) => csvCell(row[key as keyof TableRow])).join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `events-page-${page}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <>
      <section className="page-heading">
        <span className="eyebrow">Raw events</span>
        <h1>行为明细查询</h1>
        <p>按行为类型筛选原始事件，验证 Spark 统计结果可以追溯到明细数据。</p>
      </section>
      <ErrorBanner error={table.error} />
      <section className="toolbar">
        <div className="toolbar-controls">
          <label>
            <span>行为类型</span>
            <select
              aria-label="行为类型"
              value={eventType}
              onChange={(event) => {
                setPage(1);
                setSelectedRow(null);
                setEventType(event.target.value);
              }}
            >
              <option value="">全部行为</option>
              <option value="view">view</option>
              <option value="cart">cart</option>
              <option value="remove_from_cart">remove_from_cart</option>
              <option value="purchase">purchase</option>
            </select>
          </label>
          <label>
            <span>每页行数</span>
            <select
              aria-label="每页行数"
              value={pageSize}
              onChange={(event) => {
                setPage(1);
                setSelectedRow(null);
                setPageSize(Number(event.target.value));
              }}
            >
              <option value={10}>10</option>
              <option value={25}>25</option>
              <option value={50}>50</option>
            </select>
          </label>
        </div>
        <div className="toolbar-summary">
          <span>{table.isLoading ? '加载中' : `共 ${formatNumber(table.data?.total)} 条`}</span>
          <button className="secondary-action compact" type="button" disabled={!table.data?.rows.length} onClick={exportCurrentPage}>
            导出当前页
          </button>
        </div>
      </section>
      {selectedRow ? (
        <section className="row-inspector" aria-label="选中行为摘要">
          <strong>{selectedRow.event_type}</strong>
          <span>商品 {selectedRow.product_id}</span>
          <span>用户 {selectedRow.user_id}</span>
          <span>{selectedRow.event_time}</span>
        </section>
      ) : null}
      <DataTable
        data={table.data ?? null}
        isLoading={table.isLoading}
        onInspectRow={setSelectedRow}
        onSort={onSort}
        sortDirection={sortDirection}
        sortKey={sortKey}
      />
      <div className="pagination">
        <button type="button" disabled={page <= 1} onClick={() => setPage((value) => Math.max(1, value - 1))}>上一页</button>
        <span>第 {page} 页</span>
        <button type="button" disabled={!!table.data && page * table.data.size >= table.data.total} onClick={() => setPage((value) => value + 1)}>下一页</button>
      </div>
    </>
  );
}
