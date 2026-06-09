import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { MetricCard } from '../../components/MetricCard';

describe('MetricCard', () => {
  it('renders label, value and detail', () => {
    render(<MetricCard label="清洗后记录" value="960" detail="去重与异常过滤后" tone="success" />);

    expect(screen.getByText('清洗后记录')).toBeInTheDocument();
    expect(screen.getByText('960')).toBeInTheDocument();
    expect(screen.getByText('去重与异常过滤后')).toBeInTheDocument();
  });
});
