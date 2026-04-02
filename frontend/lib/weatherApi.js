import api from "./api";

export const weatherApi = {
  getIrradiance: async (planId) => {
    const response = await api.get(`/weather/irradiance/${planId}`);
    return response.data;
  },

  getCurrentWeather: async (planId) => {
    const response = await api.get(`/weather/current/${planId}`);
    return response.data;
  },

  getAnnualIrradiance: async (planId) => {
    const response = await api.get(`/weather/annual/${planId}`);
    return response.data;
  },

  getTariff: async (region = "default") => {
    const response = await api.get(`/weather/tariff?region=${region}`);
    return response.data;
  },
};