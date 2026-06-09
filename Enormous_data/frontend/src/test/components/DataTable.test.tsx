import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { tableFixture } from '../../mocks/fixtures';
import { DataTable } from '../../components/DataTable';

describe('DataTable', () => {
  it('renders ecommerce event rows', () => {
    render(<DataTable data={tableFixture} />);

    expect(screen.getByText('electronics.smartphone')).toBeInTheDocument();
    expect(screen.getByText('apple')).toBeInTheDocument();
    expect(screen.getByText('purchase')).toBeInTheDocument();
    expect(screen.getByLabelText('行为明细滚动区域')).toHaveClass('table-scroll');
    expect(screen.getByRole('table', { name: '行为明细' })).toBeInTheDocument();
  });

  it('renders an empty state', () => {
    render(<DataTable data={{ ...tableFixture, total: 0, rows: [] }} />);

    expect(screen.getByText('暂无匹配的行为记录')).toBeInTheDocument();
  });
});
