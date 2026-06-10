import { screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { QualityPage } from '../../pages/QualityPage';
import { renderWithProviders } from '../render';

vi.mock('../../components/ChartPanel', () => ({
  ChartPanel: ({ title }: { title: string }) => <div>{title}</div>,
}));

describe('QualityPage', () => {
  it('renders benchmark history and module quality evidence', async () => {
    renderWithProviders(<QualityPage />);

    expect(await screen.findByText('数据质量与清洗结果')).toBeInTheDocument();
    expect(await screen.findByText('实验质量证据')).toBeInTheDocument();
    expect(await screen.findByText('yarn_only_csv')).toBeInTheDocument();
    expect(await screen.findByText('典型模块质量')).toBeInTheDocument();
    expect(await screen.findByText('recommendation')).toBeInTheDocument();
  });
});
