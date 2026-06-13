import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { FeatureMartPage } from '../../pages/FeatureMartPage';
import { renderWithProviders } from '../render';

describe('FeatureMartPage', () => {
  it('renders feature mart governance, partition, and preview data', async () => {
    renderWithProviders(<FeatureMartPage />);

    expect(await screen.findByText('湖仓级行为事实与特征层')).toBeInTheDocument();
    expect(await screen.findByText('特征集市契约 v1')).toBeInTheDocument();
    expect(await screen.findByText('特征血缘图')).toBeInTheDocument();
    expect(await screen.findByText('日级商品行为表，用于推荐、优化和异常检测复用。')).toBeInTheDocument();
    expect(await screen.findByText('2019-10-01')).toBeInTheDocument();
    expect(await screen.findByText('1004856')).toBeInTheDocument();
    expect(await screen.findByText('536017300')).toBeInTheDocument();
  });
});
