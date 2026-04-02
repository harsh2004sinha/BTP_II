import api from "./api";

export const resultsApi = {
  runOptimization: async (planId) => {
    const response = await api.post(`/results/optimize/${planId}`);
    return response.data;
  },

  getResult: async (planId) => {
    const response = await api.get(`/results/${planId}`);
    return response.data;
  },
};