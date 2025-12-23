def print_summary(title: str, data: dict):
    print("\n" + title)
    print("-" * len(title))

    total = 0.0
    for key in sorted(data):
        val = data[key]
        sign = "+" if val >= 0 else "-"
        print(f"{key:<15} {sign}₹{abs(val):.2f}")
        total += val

    print("-" * len(title))
    sign = "+" if total >= 0 else "-"
    print(f"{'NET':<15} {sign}₹{abs(total):.2f}")
