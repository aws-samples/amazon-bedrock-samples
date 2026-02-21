import axios from 'axios'
import { OptimizerConfig, OptimizerSettings, OptimizerStatus } from '../types'

const api = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 5000,
})

export const apiService = {
  updateConfig: (config: OptimizerConfig) =>
    api.post('/update-config', config),

  runOptimizer: (settings: OptimizerSettings) =>
    api.post('/run-optimizer', settings),

  stopOptimizer: () =>
    api.post('/stop-optimizer'),

  getOptimizerStatus: (): Promise<{ data: OptimizerStatus }> =>
    api.get('/optimizer-status'),

  fetchBlueprint: (data: { project_arn: string; blueprint_id: string; project_stage: string }) =>
    api.post('/fetch-blueprint', data),

  viewLog: (logFile: string) =>
    api.get(`/view-log/${logFile}`),

  listLogs: () =>
    api.get('/list-logs'),

  cleanLogs: () =>
    api.post('/clean-logs'),

  getFinalSchema: () =>
    api.get('/final-schema'),
}