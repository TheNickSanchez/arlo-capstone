import { RunDetailView } from "../../../components/RunDetailView";

export default async function RunDetailPage({
  params,
}: {
  params: Promise<{ arloId: string }>;
}) {
  const { arloId } = await params;
  return <RunDetailView arloId={arloId} />;
}
