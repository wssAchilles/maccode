import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { OpsPage } from '../../pages/OpsPage';
import { renderWithProviders } from '../render';

describe('OpsPage', () => {
  it('renders benchmark evidence, HDFS inputs, and quality status', async () => {
    renderWithProviders(<OpsPage />);

    expect(await screen.findByText('作业治理与运行血缘')).toBeInTheDocument();
    expect(await screen.findByText('Benchmark 证据')).toBeInTheDocument();
    expect(await screen.findByText('YARN-only CSV')).toBeInTheDocument();
    expect((await screen.findAllByText('application_1780991452919_0016')).length).toBeGreaterThan(0);
    expect(await screen.findByText('实验 HDFS 输入')).toBeInTheDocument();
    expect(await screen.findByText('hdfs:///user/course/ecommerce_behavior_user_sample_1pct/*.csv')).toBeInTheDocument();
    expect(await screen.findByText('典型模块 Benchmark')).toBeInTheDocument();
    expect(await screen.findByText('recommendation_pipeline')).toBeInTheDocument();
    expect(await screen.findByText('entrypoint_ready_not_default')).toBeInTheDocument();
    expect((await screen.findAllByText('passed')).length).toBeGreaterThan(0);
  });
});
