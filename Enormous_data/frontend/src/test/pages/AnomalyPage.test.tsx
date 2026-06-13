import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { AnomalyPage } from '../../pages/AnomalyPage';
import { renderWithProviders } from '../render';

describe('AnomalyPage', () => {
  it('renders anomaly radar summary, rules, timeline, and alert evidence', async () => {
    renderWithProviders(<AnomalyPage />);

    expect(await screen.findByText('运营异常雷达')).toBeInTheDocument();
    expect(await screen.findByText('异常雷达契约 v1')).toBeInTheDocument();
    expect(await screen.findByText('类目成交额突增')).toBeInTheDocument();
    expect(await screen.findByText('严重稳健分数阈值')).toBeInTheDocument();
    expect(await screen.findByText('异常日历热力图')).toBeInTheDocument();
    expect(await screen.findByText('实际值与基线带')).toBeInTheDocument();
    expect(await screen.findByText('根因贡献瀑布图')).toBeInTheDocument();
    expect(await screen.findByRole('table', { name: '异常告警证据' })).toBeInTheDocument();
  });
});
