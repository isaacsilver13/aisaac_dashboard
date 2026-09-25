interface EventFiltersProps<T extends string> {
  label: string;
  options: T[];
  value: T | "all";
  onChange: (value: T | "all") => void;
  allLabel: string;
}

export function EventFilterGroup<T extends string>({ label, options, value, onChange, allLabel }: EventFiltersProps<T>) {
  return (
    <div className="coms-filter-group" role="group" aria-label={label}>
      <button
        type="button"
        className={value === "all" ? "coms-filter-chip active" : "coms-filter-chip"}
        onClick={() => onChange("all")}
      >
        {allLabel}
      </button>
      {options.map((option) => (
        <button
          key={option}
          type="button"
          className={value === option ? "coms-filter-chip active" : "coms-filter-chip"}
          onClick={() => onChange(option)}
        >
          {option}
        </button>
      ))}
    </div>
  );
}
