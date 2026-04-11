"use client";

import { useState, useEffect, useCallback } from "react";
import { plansApi } from "@/lib/plansApi";
import { getErrorMessage } from "@/lib/utils";
import toast from "react-hot-toast";

export function usePlans() {
  const [plans, setPlans]     = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);

  const fetchPlans = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await plansApi.getAllPlans();
      if (res.success) setPlans(res.data.plans || []);
    } catch (err) {
      const msg = getErrorMessage(err) || "Failed to load plans";
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchPlans(); }, [fetchPlans]);

  const deletePlan = useCallback(async (planId) => {
    try {
      await plansApi.deletePlan(planId);
      setPlans((prev) => prev.filter((p) => p.planId !== planId));
      toast.success("Plan deleted");
    } catch {
      toast.error("Failed to delete plan");
    }
  }, []);

  return { plans, loading, error, refetch: fetchPlans, deletePlan };
}