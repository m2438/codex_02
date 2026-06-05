export type HealthResponse = {
  status: string;
  app: string;
  mode: 'mock' | 'openai';
  database: string;
};
