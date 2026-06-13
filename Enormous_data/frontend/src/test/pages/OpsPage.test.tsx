import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { OpsPage } from '../../pages/OpsPage';
import { renderWithProviders } from '../render';

describe('OpsPage', () => {
  it('renders benchmark evidence, HDFS inputs, and quality status', async () => {
    renderWithProviders(<OpsPage />);

    expect(await screen.findByText('作业治理与运行血缘')).toBeInTheDocument();
    expect(await screen.findByText('运行阶段时间轴')).toBeInTheDocument();
    expect(await screen.findByText('产物新鲜度')).toBeInTheDocument();
    expect(await screen.findByText('Spark 资源信号')).toBeInTheDocument();
    expect(await screen.findByText('基准证据')).toBeInTheDocument();
    expect(await screen.findByText('集群 CSV 基线')).toBeInTheDocument();
    expect((await screen.findAllByText('application_1780991452919_0016')).length).toBeGreaterThan(0);
    expect(await screen.findByText('实验 HDFS 输入')).toBeInTheDocument();
    expect(await screen.findByText('hdfs:///user/course/ecommerce_behavior_user_sample_1pct/*.csv')).toBeInTheDocument();
    expect(await screen.findByText('典型模块基准')).toBeInTheDocument();
    expect(await screen.findByText('推荐流水线')).toBeInTheDocument();
    expect(await screen.findByText('规模与集群模式')).toBeInTheDocument();
    expect((await screen.findAllByText('已通过')).length).toBeGreaterThan(0);
  });
});
