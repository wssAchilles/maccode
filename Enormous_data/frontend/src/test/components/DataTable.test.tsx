import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { tableFixture } from '../../mocks/fixtures';
import { DataTable } from '../../components/DataTable';

describe('DataTable', () => {
  it('renders ecommerce event rows with sortable headers and row actions', async () => {
    const user = userEvent.setup();
    const inspect = vi.fn();
    render(<DataTable data={tableFixture} onInspectRow={inspect} />);

    expect(screen.getByText('electronics.smartphone')).toBeInTheDocument();
    expect(screen.getByText('apple')).toBeInTheDocument();
    expect(screen.getByText('purchase')).toBeInTheDocument();
    expect(screen.getByLabelText('行为明细滚动区域')).toHaveClass('table-scroll');
    expect(screen.getByRole('table', { name: '行为明细' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /时间/ })).toBeInTheDocument();

    await user.click(screen.getAllByRole('button', { name: '查看' })[0]);
    expect(inspect).toHaveBeenCalledWith(tableFixture.rows[0]);
  });

  it('renders an empty state', () => {
    render(<DataTable data={{ ...tableFixture, total: 0, rows: [] }} />);

    expect(screen.getByText('暂无匹配的行为记录')).toBeInTheDocument();
  });
});
