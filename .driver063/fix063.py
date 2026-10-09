from pathlib import Path

p = Path('driver/lib/core/localization.dart')
s = p.read_text()
s = s.replace('    "Jobs": "Joburi",\n', '', 1)
p.write_text(s)

p = Path('driver/lib/screens/earnings_screen.dart')
s = p.read_text()
s = s.replace(
    "        child: const Column(\n          children: <Widget>[\n            Icon(Icons.account_balance_wallet_outlined, size: 40),\n            SizedBox(height: 12),\n            Text('No completed jobs in this period.'.tr,",
    "        child: Column(\n          children: <Widget>[\n            const Icon(Icons.account_balance_wallet_outlined, size: 40),\n            const SizedBox(height: 12),\n            Text('No completed jobs in this period.'.tr,",
    1,
)
p.write_text(s)
print('Applied Driver v0.6.3 analyzer fixes')
