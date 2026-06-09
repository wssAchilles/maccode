import { useState } from 'react';
import { useTable } from '../api/hooks';
import { DataTable } from '../components/DataTable';
import { formatNumber } from '../lib/format';

export function TablePage() {
  const [eventType, setEventType] = useState('');
  const [page, setPage] = useState(1);
  const table = useTable({ page, size: 10, event_type: eventType });

  return (
    <>
      <section className="page-heading">
        <span className="eyebrow">Raw events</span>
        <h1>行为明细查询</h1>
        <p>按行为类型筛选原始事件，验证 Spark 统计结果可以追溯到明细数据。</p>
      </section>
      <section className="toolbar">
        <select
          value={eventType}
          onChange={(event) => {
            setPage(1);
            setEventType(event.target.value);
          }}
        >
          <option value="">全部行为</option>
          <option value="view">view</option>
          <option value="cart">cart</option>
          <option value="remove_from_cart">remove_from_cart</option>
          <option value="purchase">purchase</option>
        </select>
        <span>{table.isLoading ? '加载中' : `共 ${formatNumber(table.data?.total)} 条`}</span>
      </section>
      <DataTable data={table.data ?? null} />
      <div className="pagination">
        <button type="button" disabled={page <= 1} onClick={() => setPage((value) => Math.max(1, value - 1))}>上一页</button>
        <span>第 {page} 页</span>
        <button type="button" disabled={!!table.data && page * table.data.size >= table.data.total} onClick={() => setPage((value) => value + 1)}>下一页</button>
      </div>
    </>
  );
}
