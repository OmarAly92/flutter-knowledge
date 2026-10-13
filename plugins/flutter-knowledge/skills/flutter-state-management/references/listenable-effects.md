# Core Listenable effects primitive

Reuse an existing primitive first. When needed for the selected Listenable backend, implement this one widget in core UI; do not pretend the class exists or put it in a screen logic file. Its internal State manages framework subscription plumbing, not business state. The Screen remains StatelessWidget and supplies a callback filtering its exact effect states. Localization, snackbar and navigation extensions belong in that Screen callback.

```dart
class AppOwnerListener extends StatefulWidget {
  const AppOwnerListener({
    super.key,
    required this.owner,
    required this.onChange,
    required this.child,
  });

  final Listenable owner;
  final VoidCallback onChange;
  final Widget child;

  @override
  State<AppOwnerListener> createState() => _AppOwnerListenerState();
}

class _AppOwnerListenerState extends State<AppOwnerListener> {
  @override
  void initState() {
    super.initState();
    widget.owner.addListener(_onChange);
  }

  void _onChange() => widget.onChange();

  @override
  void didUpdateWidget(covariant AppOwnerListener oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.owner != widget.owner) {
      oldWidget.owner.removeListener(_onChange);
      widget.owner.addListener(_onChange);
    }
  }

  @override
  void dispose() {
    widget.owner.removeListener(_onChange);
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => widget.child;
}
```

Use the project's normal foundation/widgets imports. The private State is its widget's framework companion, not a second extracted Widget class. No owner is created here: it subscribes to the route-provided owner and detaches when removed or replaced.
