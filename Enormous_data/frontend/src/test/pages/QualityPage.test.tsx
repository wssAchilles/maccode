import { screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { renderWithProviders } from '../render';
import { QualityPage } from '../../pages/QualityPage';

vi.mock('../../components/ChartPanel', () => ({
  ChartPanel: ({ title }: { title: string }) => <div role="img" aria-label={title} />,
}));

describe('QualityPage', () => {
  it('renders Spark, HDFS, and History evidence from the latest job manifest', async () => {
    renderWithProviders(<QualityPage />);

    expect(await screen.findByText('数据质量与清洗结果')).toBeInTheDocument();
    expect((await screen.findAllByText('SUCCEEDED')).length).toBeGreaterThan(0);
    expect((await screen.findAllByText('application_1780989669876_0004')).length).toBeGreaterThan(0);
    expect(await screen.findByText('hdfs://master:9000/user/course/ecommerce_behavior/2019-Oct.csv')).toBeInTheDocument();
    expect(await screen.findByText('Shuffle read')).toBeInTheDocument();
  });
});
