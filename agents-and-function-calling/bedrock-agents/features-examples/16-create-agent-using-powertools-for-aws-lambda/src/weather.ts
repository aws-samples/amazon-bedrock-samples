import { logger } from './logger.js';
import type { Context } from 'aws-lambda';
import { BedrockAgentFunctionResolver } from '@aws-lambda-powertools/event-handler/bedrock-agent';
import type { BedrockAgentFunctionEvent } from '@aws-lambda-powertools/event-handler/types';
import { getPlaceInfo, getWeatherForCoordinates } from './utils.js';

const app = new BedrockAgentFunctionResolver({ logger });

app.tool<{ city: string }>(
  async ({ city }) => {
    logger.appendKeys({ city, tool: 'getWeatherForCity' });
    logger.info('getWeatherForCity called');

    try {
      const { latitude, longitude, fullName } = await getPlaceInfo(city);
      const weatherData = await getWeatherForCoordinates({
        latitude,
        longitude,
      });

      logger.info('Weather data retrieved successfully');
      return { fullName, weatherData };
    } catch (error) {
      logger.error('error retrieving weather', { error });
      return 'Sorry, I could not find the weather for that city.';
    } finally {
      logger.removeKeys(['city', 'tool']);
    }
  },
  {
    name: 'getWeatherForCity',
    description: 'Get weather for a specific city',
  }
);

export const handler = async (event: unknown, context: Context) => {
  logger.logEventIfEnabled(event);
  logger.setCorrelationId((event as BedrockAgentFunctionEvent).sessionId);
  logger.appendKeys({ requestId: context.awsRequestId });
  return app.resolve(event as BedrockAgentFunctionEvent, context);
};
