// One 100% column per year, stacked bottom-up in `groups` order; the column at breakYear gets a dashed left edge.
// The bars are hidden from assistive technology; a visually hidden table carries every year's values instead.
const StackedColumns = {
  props: { years: Array, series: Array, groups: Array, colors: Object, labels: Array, heightClass: String, breakYear: Number,
           tickEvery: { type: Number, default: 0 }, max: { type: Number, default: 100 }, gridlines: { type: Array, default: () => [] }, unit: { type: String, default: '%' } },
  setup(props) {
    const nameOf = Object.fromEntries(props.labels.map(g => [g.key, g.label]));
    const tableGroups = computed(() => props.groups.slice().reverse());
    const columns = computed(() => props.years.map((year, i) => ({
      year, shares: props.series[i],
      title: `${year}年: ` + props.groups.slice().reverse().map(g => `${nameOf[g.key]} ${props.series[i][g.key].toFixed(1)}${props.unit}`).join('、'),
    })));
    const showTick = (year, i) => i === 0 || i === props.years.length - 1 || (props.tickEvery && year % props.tickEvery === 0 && props.years.length - 1 - i >= 2 && i >= 3);
    const tickAlign = i => (i === 0 ? 'left-0' : i === props.years.length - 1 ? 'right-0' : 'left-1/2 -translate-x-1/2');
    const pct = v => (100 * v) / props.max + '%';
    return { columns, showTick, tickAlign, pct, nameOf, tableGroups };
  },
  template: `<div>
    <div class="sr-only"><table>
      <thead><tr><th scope="col">年</th><th v-for="g in tableGroups" :key="'th-' + g.key" scope="col">{{ nameOf[g.key] }}</th></tr></thead>
      <tbody><tr v-for="col in columns" :key="'tr-' + col.year"><th scope="row">{{ col.year }}</th><td v-for="g in tableGroups" :key="'td-' + col.year + g.key">{{ col.shares[g.key].toFixed(1) }}{{ unit }}</td></tr></tbody>
    </table></div>
    <div class="relative flex items-stretch gap-px" :class="heightClass" aria-hidden="true">
      <div v-for="col in columns" :key="col.year" :title="col.title" class="flex flex-1 flex-col-reverse"
        :class="col.year === breakYear ? 'border-l border-dashed border-ink pl-px dark:border-inkd' : ''">
        <span v-for="g in groups" :key="col.year + g.key" :class="colors[g.key]" :style="{ height: pct(col.shares[g.key]) }"></span>
      </div>
      <i v-for="v in gridlines" :key="'grid-' + v" class="pointer-events-none absolute inset-x-0 border-t border-dashed border-ink/40 dark:border-inkd/40" :style="{ bottom: pct(v) }"></i>
    </div>
    <div class="mt-1 flex gap-px text-[10px] tabular-nums text-muted dark:text-mutedd" aria-hidden="true">
      <span v-for="(col, i) in columns" :key="'tick-' + col.year" class="relative flex-1"><span v-if="showTick(col.year, i)" class="absolute whitespace-nowrap" :class="tickAlign(i)">{{ col.year }}</span></span>
    </div>
  </div>`,
};
