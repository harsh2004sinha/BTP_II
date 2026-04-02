import api from "./api";

export const predictionApi = {
  getPrediction: async (planId, hours = 24) => {
    const response = await api.get(
      `/prediction/${planId}?hours=${hours}`
    );
    return response.data;
  },

  refreshPrediction: async (planId) => {
    const response = await api.post(`/prediction/refresh/${planId}`);
    return response.data;
  },
};