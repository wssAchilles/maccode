import { screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { renderWithProviders } from '../render';
import { ConversionPage } from '../../pages/ConversionPage';

vi.mock('../../components/ChartPanel', () => ({
  ChartPanel: ({ title }: { title: string }) => <section>{title}</section>,
}));

describe('ConversionPage', () => {
  it('renders conversion KPIs and product table', async () => {
    renderWithProviders(<ConversionPage />);

    expect(await screen.findByText('会话转化智能分析')).toBeInTheDocument();
    expect(await screen.findByText('24.62%')).toBeInTheDocument();
    expect(await screen.findByText('1004856')).toBeInTheDocument();
    expect(await screen.findByText('samsung')).toBeInTheDocument();
  });
});
