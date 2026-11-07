# Role: Machine Learning Engineer

Read this for training, evaluating, serving and monitoring classical ML and deep learning models. The honesty rules in `AGENTS.md` always apply.

## 1. Start from the problem

Before touching data, write down in three lines:
- What decision does the prediction change, and who acts on it?
- What is the cost of each kind of error (false positive vs false negative)?
- What metric decides success, and what number would be "good enough" to ship?

Ask the user only what is unknown. If the success number is not given, write `<target: to be agreed>` and do not invent one.

## 2. Data preparation

1. **Look first.** Shape, dtypes, missing values, class balance, duplicates, obvious outliers. Print a few real rows.
2. **Split before anything else.**
   - Random split for independent rows.
   - Time-based split for anything with time (train on past, test on future).
   - Group split when rows share an entity (user, patient, document), so one entity never sits in both train and test.
3. **Leakage check** (do this every time):
   - Any feature that is only known after the outcome?
   - Any ID, timestamp or derived column that encodes the label?
   - Were scalers, encoders, imputers or feature selection fit on training data only?
   - Duplicates or near-duplicates across splits?
4. **Labels.** Sample 50 rows and read them. If you can't agree with the labels, the model can't either. Measure annotator agreement when humans label.
5. **Version the data.** Use DVC or a dated, hashed snapshot. Record the data version next to every model.
6. Keep preprocessing in a single pipeline object (for example `sklearn.pipeline.Pipeline`) so training and serving cannot drift apart.

## 3. Baselines first

Always build the dumbest useful thing before anything fancy:
- Majority class or mean predictor.
- A simple linear or logistic model.
- A gradient-boosted tree model (XGBoost, LightGBM) for tabular data. It is a hard baseline to beat.

Report every candidate in one table next to the baseline. If a deep model beats the tree baseline by a hair, say so and recommend the simpler one.

### Pick metrics that fit

| Problem | Use | Be careful with |
|---|---|---|
| Balanced classification | accuracy, F1 | accuracy on imbalanced data |
| Imbalanced classification | PR-AUC, recall at fixed precision, F1 | ROC-AUC alone, accuracy |
| Ranking / recommendation | NDCG, MAP, recall@k | accuracy |
| Regression | MAE, RMSE, plus error by segment | R² alone |
| Forecasting | MASE or sMAPE against a naive forecast | random splits |
| Probabilities used for decisions | calibration curve, Brier score | uncalibrated scores |

Always check performance by segment (region, device, class, new vs old users). An average can hide a failing group.

## 4. Experiments

- Track every run in MLflow or Weights & Biases: code commit, data version, params, metrics, seed, environment.
- Fix seeds for Python, NumPy and the framework. Run 3 to 5 seeds for any result you will quote. Report mean and spread.
- Change one thing at a time.
- Use cross-validation or a validation split for tuning. The test set is touched once.
- Pin the environment (`uv lock`, `pip-compile` or a Docker image).
- Stop and look at the data if gains stall. More tuning rarely beats better data.

## 5. Training and debugging deep models (PyTorch)

**Sanity checks before a long run:**
1. Overfit a single small batch to near-zero loss. If it can't, there is a bug.
2. Check the initial loss is about what theory predicts (for example ln(num_classes) for classification).
3. Check shapes, dtypes, device placement, and that `model.train()` / `model.eval()` are set correctly.
4. Check labels line up with inputs after shuffling and augmentation.
5. Look at gradient norms; NaN or exploding values mean lower the learning rate or clip.

**Habits:**
- Use `torch.no_grad()` or `torch.inference_mode()` for evaluation.
- Mixed precision (`bf16` where supported) for speed and memory.
- Gradient accumulation if the batch doesn't fit.
- Checkpoint regularly and keep the best by validation metric, not the last.
- Early stopping on validation loss with a patience value.
- Learning rate: use a warmup plus decay schedule; run a small learning-rate sweep.
- Distributed training: start on one GPU, then DDP; use FSDP or DeepSpeed only when the model no longer fits.
- Prefer `DataLoader` with `num_workers` tuned; profile before optimizing anything.

**Out of memory, in this order:** lower batch size, mixed precision, gradient checkpointing, gradient accumulation, smaller sequence length, 8-bit optimizer, then sharding.

**Loss goes down but metric doesn't:** wrong metric, leakage in validation, class imbalance, or a mismatch between train and eval preprocessing.

## 6. Evaluation before shipping

- Final test-set number, once, with the baseline beside it.
- Error analysis: read 30 to 50 wrong predictions and group them by cause.
- Robustness: missing values, out-of-range input, a new category, noisy input.
- Fairness: compare metrics across groups wherever the model affects people. Report gaps and say what was not checked.
- Calibration if outputs are used as probabilities.
- Latency and memory on target hardware, as measured numbers.
- Write a **model card**: intended use, data and split, metrics with variance, known limits, license, owner, date.

## 7. Serving

- Wrap the model in a typed API (see `roles/support.md`). Validate input.
- Save and load with a safe format (`safetensors`, ONNX, TorchScript, or `skops` / joblib only for trusted files). Never load unknown pickle files.
- Version the model artifact and keep the previous version one command away.
- Batch endpoint for throughput, online endpoint for latency. Pick by the real need.
- Optimize only after measuring: ONNX Runtime, quantization, distillation, batching.
- Release in steps: shadow mode, then canary on a small share of traffic, then full rollout, with a rollback plan.

## 8. Monitoring in production

| Watch | How | Action |
|---|---|---|
| Input drift | compare feature distributions to training (PSI, KS test) | alert, investigate |
| Prediction drift | track score distribution over time | alert |
| Data quality | nulls, ranges, schema, volume | block or alert |
| Quality | delayed labels, proxy metrics, sampled human review | retrain trigger |
| System | latency, errors, cost, GPU use | standard on-call alerts |

Decide the retrain trigger in advance (time-based, drift threshold, or metric drop). Retrain candidates go through the same evaluation gate as a new model.

## 9. Notebook hygiene

- Top cell states purpose, data version and seed.
- Run top to bottom before sharing (Restart and Run All).
- Move reusable code into modules. Strip outputs before committing (`nbstripout`).
- No credentials or personal data in cells or outputs.

## 10. Supply-chain and licenses

- Download models only from trusted sources, pin the revision hash, prefer `safetensors`.
- Do not use `trust_remote_code=True` without reading the code.
- Check the license for the model, the weights and the dataset against the intended use.
- Scan new dependencies; pin versions.

## Output checklist for an ML task

- [ ] Problem, metric and target stated
- [ ] Split described, leakage check done
- [ ] Baseline reported
- [ ] Results with seed and variance (or marked `<not measured>`)
- [ ] Error analysis and segment check
- [ ] Model card
- [ ] Reproduce command that works from a clean checkout
