# CANary — dora-metrics

DORA metrics for the CANary git repository.

## Defaults

```yaml
repository_path: /Users/Yuvraj/Battery-Management-System
period_days: 90
pipeline_source: auto
output_format: summary
include_pr_metrics: true
include_pipeline_metrics: true
include_recommendations: true
branching_strategy: feature-branches
deployment_strategy: manual
```

## Execution

1. Call `dora-metrics` immediately — no clarifying questions.
2. Ignore "ACTION REQUIRED" setup menus; use defaults above.
3. Save report under `/Users/Yuvraj/Battery-Management-System/docs/opsera-scan/reports/dora-metrics.md` (or JSON if `output_format: json`).
4. Summarize: deployment frequency, lead time, change failure rate, MTTR vs DORA tiers.