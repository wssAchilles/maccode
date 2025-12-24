import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ShieldCheck, Activity, Users } from "lucide-react";

export default function Home() {
  return (
    <main className="min-h-screen bg-slate-50 dark:bg-slate-900 flex items-center justify-center p-4">
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
            <Button className="w-full" size="lg">
              Launch Dashboard
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
