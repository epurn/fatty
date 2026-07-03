import type { TargetReadModel } from '@/api/dailySummary';
import type { GoalDirection, PacePreset } from '@/api/goals';
import type { ProfileDTO } from '@/api/profile';
import type { MetabolicFormula } from '@/state/profile';

const PACE_LABELS: Record<PacePreset, string> = {
  gentle: 'Gentle',
  steady: 'Steady',
  faster: 'Faster',
};

const DIRECTION_LABELS: Record<GoalDirection, string> = {
  loss: 'Lose',
  maintain: 'Maintain',
  gain: 'Gain',
};

const PLANNING_HORIZON_DAYS = 84;
// Mirrors docs/contracts/target-calculator.md just far enough to recover the
// display pace from an already-loaded target. Ambiguous values stay neutral.
const BASELINE_ACTIVITY_MULTIPLIER = 1.2;
const ENERGY_DENSITY_KCAL_PER_KG = 7700;
const RMR_MASS_COEFFICIENT_KCAL_PER_KG = 10;
const MIFFLIN_HEIGHT_COEFFICIENT_KCAL_PER_CM = 6.25;
const MIFFLIN_AGE_COEFFICIENT_KCAL_PER_YEAR = 5;
const MIFFLIN_CONSTANTS: Record<MetabolicFormula, number> = {
  mifflin_st_jeor_plus5: 5,
  mifflin_st_jeor_minus161: -161,
};
const SAFETY_FLOOR_KCAL: Record<MetabolicFormula, number> = {
  mifflin_st_jeor_plus5: 1500,
  mifflin_st_jeor_minus161: 1200,
};
const SAFETY_CEILING_KCAL = 4000;
const PROTEIN_G_PER_KG = 1.6;
const FAT_PCT_OF_CALORIES = 0.3;
const FAT_FLOOR_G_PER_KG = 0.8;
const KCAL_PER_G_PROTEIN = 4;
const KCAL_PER_G_CARB = 4;
const KCAL_PER_G_FAT = 9;
const PACE_WEEKLY_FRACTION: Record<
  Exclude<GoalDirection, 'maintain'>,
  readonly { readonly pace: PacePreset; readonly fraction: number }[]
> = {
  loss: [
    { pace: 'gentle', fraction: 0.0025 },
    { pace: 'steady', fraction: 0.005 },
    { pace: 'faster', fraction: 0.01 },
  ],
  gain: [
    { pace: 'gentle', fraction: 0.00125 },
    { pace: 'steady', fraction: 0.0025 },
  ],
};
const TARGET_INFERENCE_CALORIE_TOLERANCE = 12;
const TARGET_INFERENCE_MACRO_TOLERANCE = 3;

export function goalSummaryDetail(
  direction: GoalDirection | null,
  pace: PacePreset | null | undefined,
): string {
  if (direction === null) return 'Details unavailable';
  if (direction !== 'maintain' && !pace) return 'Details unavailable';
  return `${DIRECTION_LABELS[direction]}${pace && direction !== 'maintain' ? ` · ${PACE_LABELS[pace]}` : ''}`;
}

function metabolicFormula(value: ProfileDTO['metabolic_formula']): MetabolicFormula | null {
  return value === 'mifflin_st_jeor_plus5' || value === 'mifflin_st_jeor_minus161'
    ? value
    : null;
}

function profileYear(profile: ProfileDTO, date: Date): number {
  try {
    const parts = new Intl.DateTimeFormat('en-US', {
      timeZone: profile.timezone,
      year: 'numeric',
    }).formatToParts(date);
    const year = Number(parts.find((part) => part.type === 'year')?.value);
    return Number.isFinite(year) ? year : date.getFullYear();
  } catch {
    return date.getFullYear();
  }
}

function roundHalfUp(value: number): number {
  return Math.floor(value + 0.5);
}

function derivedTargetForPace({
  profile,
  startWeightKg,
  direction,
  paceFraction,
  today,
}: {
  profile: ProfileDTO;
  startWeightKg: number;
  direction: Exclude<GoalDirection, 'maintain'>;
  paceFraction: number;
  today: Date;
}): { calories: number; carbsG: number; fatG: number } | null {
  const formula = metabolicFormula(profile.metabolic_formula);
  if (formula === null || profile.height_m === null || profile.birth_year === null) {
    return null;
  }

  const ageYears = profileYear(profile, today) - profile.birth_year;
  const weightIndependentRmr =
    MIFFLIN_HEIGHT_COEFFICIENT_KCAL_PER_CM * (profile.height_m * 100) -
    MIFFLIN_AGE_COEFFICIENT_KCAL_PER_YEAR * ageYears +
    MIFFLIN_CONSTANTS[formula];
  const targetWeightKg =
    direction === 'loss'
      ? startWeightKg - paceFraction * startWeightKg * (PLANNING_HORIZON_DAYS / 7)
      : startWeightKg + paceFraction * startWeightKg * (PLANNING_HORIZON_DAYS / 7);
  const k =
    (BASELINE_ACTIVITY_MULTIPLIER * RMR_MASS_COEFFICIENT_KCAL_PER_KG) /
    ENERGY_DENSITY_KCAL_PER_KG;
  const e = Math.exp(-k * PLANNING_HORIZON_DAYS);
  const equilibriumWeight = (targetWeightKg - startWeightKg * e) / (1 - e);
  const rawTarget =
    BASELINE_ACTIVITY_MULTIPLIER *
    (weightIndependentRmr + RMR_MASS_COEFFICIENT_KCAL_PER_KG * equilibriumWeight);
  const roundedTarget = Math.round(rawTarget);
  const calories = Math.max(
    SAFETY_FLOOR_KCAL[formula],
    Math.min(SAFETY_CEILING_KCAL, roundedTarget),
  );
  const fatFromShareG = roundHalfUp(
    (FAT_PCT_OF_CALORIES * calories) / KCAL_PER_G_FAT,
  );
  const fatFloorG = roundHalfUp(FAT_FLOOR_G_PER_KG * startWeightKg);
  const fatG = Math.max(fatFromShareG, fatFloorG);
  const proteinG = roundHalfUp(PROTEIN_G_PER_KG * startWeightKg);
  const carbsKcal =
    calories - KCAL_PER_G_PROTEIN * proteinG - KCAL_PER_G_FAT * fatG;
  const carbsG = roundHalfUp(Math.max(0, carbsKcal) / KCAL_PER_G_CARB);
  return { calories, carbsG, fatG };
}

export function inferLoadedGoalPace({
  direction,
  profile,
  target,
  today,
}: {
  direction: GoalDirection | null;
  profile: ProfileDTO | null;
  target: TargetReadModel | null;
  today: Date;
}): PacePreset | null {
  if (direction === null || direction === 'maintain' || profile === null || target === null) {
    return null;
  }

  const startWeightKg = target.protein_g.derived / PROTEIN_G_PER_KG;
  if (!Number.isFinite(startWeightKg) || startWeightKg <= 0) {
    return null;
  }

  const matches = PACE_WEEKLY_FRACTION[direction].filter(({ fraction }) => {
    const candidate = derivedTargetForPace({
      profile,
      startWeightKg,
      direction,
      paceFraction: fraction,
      today,
    });
    return (
      candidate !== null &&
      Math.abs(candidate.calories - target.calories.derived) <=
        TARGET_INFERENCE_CALORIE_TOLERANCE &&
      Math.abs(candidate.carbsG - target.carbs_g.derived) <=
        TARGET_INFERENCE_MACRO_TOLERANCE &&
      Math.abs(candidate.fatG - target.fat_g.derived) <=
        TARGET_INFERENCE_MACRO_TOLERANCE
    );
  });

  return matches.length === 1 ? matches[0].pace : null;
}
