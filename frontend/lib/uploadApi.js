import api from "./api";

export const uploadApi = {
  uploadBill: async (planId, file, onProgress) => {
    const formData = new FormData();
    formData.append("file", file);

    const response = await api.post(`/upload/bill/${planId}`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
      onUploadProgress: (progressEvent) => {
        if (onProgress) {
          const percent = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          onProgress(percent);
        }
      },
    });
    return response.data;
  },

  getConsumption: async (planId) => {
    const response = await api.get(`/upload/consumption/${planId}`);
    return response.data;
  },

  addManualConsumption: async (planId, monthlyUnits, pattern = "flat") => {
    const response = await api.post(
      `/upload/manual/${planId}?monthly_units=${monthlyUnits}&pattern=${pattern}`
    );
    return response.data;
  },
};