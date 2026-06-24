import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { FeatureMartPage } from '../../pages/FeatureMartPage';
import { renderWithProviders } from '../render';

describe('FeatureMartPage', () => {
  it('renders feature mart governance, partition, and preview data', async () => {
    renderWithProviders(<FeatureMartPage />);

    expect(await screen.findByText('湖仓级行为事实与特征层')).toBeInTheDocument();
    expect(await screen.findByText('特征集市契约 v1')).toBeInTheDocument();
    expect(await screen.findByText('每种特征层都有入口，点击后联动类目、字典和样本')).toBeInTheDocument();
    expect(await screen.findByText('商品特征层')).toBeInTheDocument();
    expect(await screen.findByText('类目特征层')).toBeInTheDocument();
    expect(await screen.findByText('用户特征层')).toBeInTheDocument();
    expect(await screen.findByRole('button', { name: /appliances/ })).toBeInTheDocument();
    expect(await screen.findByText('底层数据图回答 4 个问题')).toBeInTheDocument();
    expect(await screen.findByText('4. 特征血缘图')).toBeInTheDocument();
    expect(await screen.findByText('日级商品行为表，用于推荐、优化和异常检测复用。')).toBeInTheDocument();
    expect(await screen.findByText('2019-10-01')).toBeInTheDocument();
    expect((await screen.findAllByText('1004856')).length).toBeGreaterThan(0);
    expect(await screen.findByText('536017300')).toBeInTheDocument();
  });

  it('links feature layer and category selections to the preview table', async () => {
    const user = userEvent.setup();
    renderWithProviders(<FeatureMartPage />);

    await user.click(await screen.findByRole('button', { name: /用户特征层/ }));
    expect(await screen.findByText('用户粒度代表样本')).toBeInTheDocument();
    expect((await screen.findAllByText('用户偏好一级类目')).length).toBeGreaterThan(0);

    await user.click(await screen.findByRole('button', { name: /appliances/ }));
    expect((await screen.findAllByText('512880901')).length).toBeGreaterThan(0);
  });
});
