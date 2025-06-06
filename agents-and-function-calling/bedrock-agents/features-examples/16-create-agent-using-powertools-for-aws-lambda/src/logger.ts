import { Logger } from '@aws-lambda-powertools/logger';

const logger = new Logger({
  logLevel: 'debug',
  serviceName: 'weather-agent',
});

export { logger };
