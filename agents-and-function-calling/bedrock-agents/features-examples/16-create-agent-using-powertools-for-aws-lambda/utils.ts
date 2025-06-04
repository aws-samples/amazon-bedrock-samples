import {
  GeoPlacesClient,
  AutocompleteCommand,
  GetPlaceCommand,
} from '@aws-sdk/client-geo-places';
import { logger } from './logger.js';

const geoClient = new GeoPlacesClient();

/**
 * Look up a city by its name and return its full name and coordinates.
 *
 * This function uses Amazon Location Service to look up the coordinates
 * of a city by its name. It first performs an autocomplete search
 * to get the place ID, and then retrieves the coordinates using that ID.
 *
 * @example
 * ```ts
 * import { getPlaceInfo } from './utils.js';
 *
 * const { latitude, longitude } = await getPlaceInfo('Seattle');
 * ```
 *
 * @param city - The name of the city to get coordinates for
 */
const getPlaceInfo = async (city: string) => {
  let placeId: string;
  try {
    const response = await geoClient.send(
      new AutocompleteCommand({
        QueryText: city,
        MaxResults: 1,
      })
    );
    logger.debug('Autocomplete response', { response });
    if (
      response.ResultItems &&
      response.ResultItems.length > 0 &&
      response.ResultItems[0].PlaceId
    ) {
      placeId = response.ResultItems[0].PlaceId;
      logger.debug('Place ID found', { placeId });
    } else {
      throw new Error('No place found');
    }
  } catch (error) {
    logger.error('Error in AutocompleteCommand', { error });
    throw new Error('Error in AutocompleteCommand');
  }

  try {
    const response = await geoClient.send(
      new GetPlaceCommand({
        PlaceId: placeId,
      })
    );
    logger.debug('GetPlace response', { response });
    if (response.Position) {
      const [longitude, latitude] = response.Position;
      logger.debug('Coordinates found', { latitude, longitude });
      return { latitude, longitude, fullName: response.Title };
    }
    throw new Error('No coordinates found');
  } catch (error) {
    logger.error('Error in GetPlaceCommand', { error });
    throw new Error('Error in GetPlaceCommand');
  }
};

/**
 * Get the current weather for a given set of coordinates.
 *
 * The function fetches the current temperature and wind speed
 * using the {@link https://open-meteo.com | Open Meteo API} based on the provided latitude and longitude.
 *
 * @example
 * ```ts
 * import { getWeatherForCoordinates } from './utils.js';
 *
 * const weatherData = await getWeatherForCoordinates({
 *   latitude: 47.6062,
 *   longitude: -122.3321,
 * });
 * ```
 *
 * @param coordinates - The coordinates of the city
 * @param coordinates.latitude - The latitude of the city
 * @param coordinates.longitude - The longitude of the city
 */
const getWeatherForCoordinates = async (coordinates: {
  latitude: number;
  longitude: number;
}) => {
  const { latitude, longitude } = coordinates;
  try {
    const res = await fetch(
      `https://api.open-meteo.com/v1/forecast?latitude=${latitude}&longitude=${longitude}&current=temperature_2m,wind_speed_10m`
    );
    if (!res.ok) {
      throw new Error('Failed to fetch weather data', {
        cause: res.statusText,
      });
    }
    return await res.text();
  } catch (error) {
    logger.error('Error fetching weather data', { error });
    throw new Error('Error fetching weather data');
  }
};

export { getPlaceInfo, getWeatherForCoordinates };
