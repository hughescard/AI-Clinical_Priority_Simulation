interface LoadingStateProps {
  title: string;
  description: string;
}

export function LoadingState({ title, description }: LoadingStateProps) {
  return (
    <div className="rounded-[2rem] border border-emerald-100 bg-emerald-50/80 px-6 py-8">
      <div className="flex items-center gap-4">
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-emerald-200 border-t-emerald-700" />
        <div>
          <h3 className="text-lg font-semibold text-emerald-900">{title}</h3>
          <p className="mt-1 text-sm text-emerald-700">{description}</p>
        </div>
      </div>
    </div>
  );
}

