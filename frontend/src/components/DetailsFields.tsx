/**
 * Campos de `details` según el tipo de emergencia (§5.1 y §9).
 *
 * La forma de cada bloque es exactamente la del union discriminado que valida
 * Intake: mandar un campo de otro tipo devolvería INVALID_PAYLOAD.
 */
import type { EmergencyType } from '../lib/types'

export type DetailsState = Record<string, unknown>

/** Valores iniciales por tipo. Coinciden con los que asume el triage cuando un
 *  campo no viene: 0 y false. */
export function initialDetails(type: EmergencyType): DetailsState {
  switch (type) {
    case 'RESCUE':
      return { injured: 0, trapped: 0, fire: false, gasLeak: false }
    case 'SHELTER':
      return {
        adults: 0,
        children: 0,
        elderly: 0,
        accessibilityRequired: false,
        houseHabitable: false,
      }
    case 'SUPPLIES':
      return { categories: [], people: 0 }
    case 'STRUCTURAL_DAMAGE':
      return {
        buildingType: 'RESIDENTIAL',
        crackLevel: 'LOW',
        collapseRisk: false,
      }
  }
}

const SUPPLY_CATEGORIES = ['WATER', 'FOOD', 'MEDICINE', 'HYGIENE', 'SHELTER_KIT']

const CATEGORY_LABELS: Record<string, string> = {
  WATER: 'Agua',
  FOOD: 'Alimentos',
  MEDICINE: 'Medicamentos',
  HYGIENE: 'Aseo',
  SHELTER_KIT: 'Kit de albergue',
}

function NumberField({
  label,
  value,
  onChange,
}: {
  label: string
  value: number
  onChange: (value: number) => void
}) {
  return (
    <label className="block">
      <span className="text-sm font-medium text-slate-700">{label}</span>
      <input
        type="number"
        min={0}
        value={value}
        onChange={(e) => onChange(Math.max(0, Number(e.target.value) || 0))}
        className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 focus:border-slate-500 focus:outline-none"
      />
    </label>
  )
}

function CheckField({
  label,
  checked,
  onChange,
}: {
  label: string
  checked: boolean
  onChange: (checked: boolean) => void
}) {
  return (
    <label className="flex items-center gap-2">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="h-4 w-4 rounded border-slate-300"
      />
      <span className="text-sm text-slate-700">{label}</span>
    </label>
  )
}

export function DetailsFields({
  type,
  details,
  onChange,
}: {
  type: EmergencyType
  details: DetailsState
  onChange: (details: DetailsState) => void
}) {
  const set = (key: string, value: unknown) =>
    onChange({ ...details, [key]: value })

  if (type === 'RESCUE') {
    return (
      <div className="grid gap-4 sm:grid-cols-2">
        <NumberField
          label="Personas heridas"
          value={details.injured as number}
          onChange={(v) => set('injured', v)}
        />
        <NumberField
          label="Personas atrapadas"
          value={details.trapped as number}
          onChange={(v) => set('trapped', v)}
        />
        <CheckField
          label="Hay fuego"
          checked={details.fire as boolean}
          onChange={(v) => set('fire', v)}
        />
        <CheckField
          label="Hay fuga de gas"
          checked={details.gasLeak as boolean}
          onChange={(v) => set('gasLeak', v)}
        />
      </div>
    )
  }

  if (type === 'SHELTER') {
    return (
      <div className="grid gap-4 sm:grid-cols-3">
        <NumberField
          label="Adultos"
          value={details.adults as number}
          onChange={(v) => set('adults', v)}
        />
        <NumberField
          label="Niños"
          value={details.children as number}
          onChange={(v) => set('children', v)}
        />
        <NumberField
          label="Adultos mayores"
          value={details.elderly as number}
          onChange={(v) => set('elderly', v)}
        />
        <div className="sm:col-span-3 space-y-2">
          <CheckField
            label="Se requiere accesibilidad"
            checked={details.accessibilityRequired as boolean}
            onChange={(v) => set('accessibilityRequired', v)}
          />
          <CheckField
            label="La vivienda sigue siendo habitable"
            checked={details.houseHabitable as boolean}
            onChange={(v) => set('houseHabitable', v)}
          />
        </div>
      </div>
    )
  }

  if (type === 'SUPPLIES') {
    const categories = (details.categories as string[]) ?? []
    return (
      <div className="space-y-4">
        <NumberField
          label="Personas que necesitan suministros"
          value={details.people as number}
          onChange={(v) => set('people', v)}
        />
        <fieldset>
          <legend className="text-sm font-medium text-slate-700">
            Categorías necesarias
          </legend>
          <div className="mt-2 grid gap-2 sm:grid-cols-3">
            {SUPPLY_CATEGORIES.map((category) => (
              <CheckField
                key={category}
                label={CATEGORY_LABELS[category]}
                checked={categories.includes(category)}
                onChange={(checked) =>
                  set(
                    'categories',
                    checked
                      ? [...categories, category]
                      : categories.filter((c) => c !== category),
                  )
                }
              />
            ))}
          </div>
        </fieldset>
      </div>
    )
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <label className="block">
        <span className="text-sm font-medium text-slate-700">
          Tipo de edificación
        </span>
        <select
          value={details.buildingType as string}
          onChange={(e) => set('buildingType', e.target.value)}
          className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
        >
          <option value="RESIDENTIAL">Vivienda</option>
          <option value="COMMERCIAL">Comercio</option>
          <option value="SCHOOL">Colegio</option>
          <option value="HOSPITAL">Hospital</option>
          <option value="OTHER">Otro</option>
        </select>
      </label>
      <label className="block">
        <span className="text-sm font-medium text-slate-700">
          Nivel de fisuras
        </span>
        <select
          value={details.crackLevel as string}
          onChange={(e) => set('crackLevel', e.target.value)}
          className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
        >
          <option value="LOW">Bajo</option>
          <option value="MEDIUM">Medio</option>
          <option value="HIGH">Alto</option>
        </select>
      </label>
      <div className="sm:col-span-2">
        <CheckField
          label="Hay riesgo de colapso"
          checked={details.collapseRisk as boolean}
          onChange={(v) => set('collapseRisk', v)}
        />
      </div>
    </div>
  )
}
