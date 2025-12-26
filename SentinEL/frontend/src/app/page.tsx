"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ShieldCheck, Activity, Users } from "lucide-react";
import { useState } from "react";
import { useToast } from "@/hooks/use-toast";
import { Toaster } from "@/components/ui/toaster";

export default function Home() {
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);

  const handleAnalyze = async () => {
    setLoading(true);
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
    try {
      const response = await fetch(`${apiUrl}/api/v1/analyze`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": "sentinel_top_secret_2025",
        },
        body: JSON.stringify({ user_id: "63826" }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const initialData = await response.json();
      const analysisId = initialData.analysis_id;

      // Polling for results
      let attempts = 0;
      const maxAttempts = 20; // 20 seconds timeout
      let resultData = null;

      while (attempts < maxAttempts) {
        await new Promise(resolve => setTimeout(resolve, 1000)); // Wait 1s
        const statusRes = await fetch(`${apiUrl}/api/v1/analyze/${analysisId}`);
        if (statusRes.ok) {
          const statusData = await statusRes.json();
          if (statusData.status === 'COMPLETED') {
            resultData = statusData;
            break;
          }
        }
        attempts++;
      }

      if (!resultData) {
        throw new Error("Analysis timed out");
      }

      const data = resultData;

      toast({
        title: "Analysis Complete",
        description: `Risk Level: ${data.risk_level} (${(data.churn_probability * 100).toFixed(1)}%)`,
        variant: data.risk_level === "High" ? "destructive" : "default",
      });

      console.log("Analysis Result:", data);

    } catch (error) {
      console.error("Analysis Failed:", error);
      toast({
        title: "Connection Failed",
        description: "Could not connect to SentinEL Backend.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-slate-50 dark:bg-slate-900 flex items-center justify-center p-4">
      <Toaster />
      <Card className="w-full max-w-md shadow-lg border-t-4 border-t-primary">
        <CardHeader className="text-center">
          <div className="mx-auto bg-primary/10 p-3 rounded-full w-fit mb-4">
            <ShieldCheck className="w-10 h-10 text-primary" />
          </div>
          <CardTitle className="text-2xl font-bold text-slate-900 dark:text-white">
            SentinEL Enterprise
          </CardTitle>
          <CardDescription>
            High-Precision User Retention AI Platform
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-white dark:bg-slate-800 p-3 rounded-lg border shadow-sm flex flex-col items-center">
              <Activity className="w-5 h-5 text-blue-500 mb-1" />
              <span className="text-xs text-slate-500">System Status</span>
              <Badge variant="outline" className="mt-1 text-green-600 border-green-200 bg-green-50">
                Online
              </Badge>
            </div>
            <div className="bg-white dark:bg-slate-800 p-3 rounded-lg border shadow-sm flex flex-col items-center">
              <Users className="w-5 h-5 text-purple-500 mb-1" />
              <span className="text-xs text-slate-500">Active Users</span>
              <span className="font-bold text-slate-900 dark:text-white">12,450</span>
            </div>
          </div>

          <div className="space-y-2">
            <Button
              className="w-full"
              size="lg"
              onClick={handleAnalyze}
              disabled={loading}
            >
              {loading ? "Analyzing..." : "Launch Dashboard"}
            </Button>
            <Button variant="ghost" className="w-full text-slate-500">
              View Documentation
            </Button>
          </div>
        </CardContent>
      </Card>
    </main>
  );
}
