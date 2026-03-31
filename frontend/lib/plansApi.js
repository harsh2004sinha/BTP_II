import api from "./api";

export const plansApi = {
  createPlan: async (data) => {
    const response = await api.post("/plans/createPlan", data);
    return response.data;
  },

  getAllPlans: async () => {
    const response = await api.get("/plans/all");
    return response.data;
  },

  getPlan: async (planId) => {
    const response = await api.get(`/plans/${planId}`);
    return response.data;
  },

  updatePlan: async (planId, data) => {
    const response = await api.put(`/plans/${planId}`, data);
    return response.data;
  },

  deletePlan: async (planId) => {
    const response = await api.delete(`/plans/${planId}`);
    return response.data;
  },
};