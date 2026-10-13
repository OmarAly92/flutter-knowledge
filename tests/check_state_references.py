import argparse
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def assemble(project):
    root = ROOT
    lib = project / 'lib'
    lib.mkdir(exist_ok=True)
    contracts='''import 'package:equatable/equatable.dart';
    class XModel extends Equatable {
      final String? name;
      const XModel({this.name});
      @override
      List<Object?> get props => [name];
    }
    class Failure extends Equatable {
      const Failure(this.message);
      final String message;
      @override
      List<Object?> get props => [message];
    }
    class GlobalResponse<T> {
      const GlobalResponse({this.data});
      final T? data;
    }
    sealed class FetchResult {
      const FetchResult();
      void when({required void Function(GlobalResponse<XModel>) onSuccess, required void Function(Failure) onFailure});
    }
    final class FetchSuccess extends FetchResult {
      const FetchSuccess(this.response);
      final GlobalResponse<XModel> response;
      @override
      void when({required void Function(GlobalResponse<XModel>) onSuccess, required void Function(Failure) onFailure}) => onSuccess(response);
    }
    final class FetchFailure extends FetchResult {
      const FetchFailure(this.failure);
      final Failure failure;
      @override
      void when({required void Function(GlobalResponse<XModel>) onSuccess, required void Function(Failure) onFailure}) => onFailure(failure);
    }
    abstract class XRepository {
      Future<FetchResult> getX();
    }
    '''
    (lib/'contracts.dart').write_text(contracts)
    state='''sealed class XState extends Equatable {
      const XState();
      @override
      List<Object?> get props => [];
    }
    final class XInitialState extends XState { const XInitialState(); }
    final class GetXLoadingState extends XState { const GetXLoadingState(); }
    final class GetXSuccessState extends XState { const GetXSuccessState(); }
    final class GetXFailureState extends XState {
      const GetXFailureState({required this.failure});
      final Failure failure;
      @override
      List<Object?> get props => [failure];
    }
    '''
    imports={'cubit':"import 'package:bloc/bloc.dart';",'riverpod':"import 'package:flutter_riverpod/flutter_riverpod.dart';",'provider':"import 'package:flutter/foundation.dart';"}
    for backend in imports:
     source=(root/f'plugins/flutter-knowledge/skills/flutter-state-management/references/{backend}.md').read_text()
     blocks=re.findall(r'```dart\n(.*?)```',source,re.S)
     owner=blocks[0]
     text=f"import 'package:equatable/equatable.dart';\nimport '../contracts.dart';\n{imports[backend]}\npart 'x_state.dart';\n"+owner
     if backend=='riverpod':text+='\n'+blocks[1]
     dest=lib/backend;dest.mkdir(exist_ok=True);(dest/'x_cubit.dart').write_text(text)
     (dest/'x_state.dart').write_text("part of 'x_cubit.dart';\n"+state)
    listener=(root/'plugins/flutter-knowledge/skills/flutter-state-management/references/listenable-effects.md').read_text()
    (lib/'app_owner_listener.dart').write_text("import 'package:flutter/widgets.dart';\n"+re.findall(r'```dart\n(.*?)```',listener,re.S)[0])
    test=project/'test';test.mkdir(exist_ok=True)
    (test / 'owner_test.dart').write_text((ROOT / 'tests/state_reference_test.dart').read_text())


def main():
    parser = argparse.ArgumentParser(description='Compile and exercise the state-reference recipes in an isolated Flutter fixture.')
    parser.add_argument('--riverpod-version', choices=['2.6.1', '3.4.3'], default='3.4.3')
    parser.add_argument('--fetch', action='store_true', help='Permit dependency downloads for this temporary fixture')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='flutter-state-reference-') as folder:
        project = Path(folder)
        pubspec = f"""name: state_reference_check
environment:
  sdk: ">=3.9.0 <4.0.0"
dependencies:
  flutter:
    sdk: flutter
  flutter_riverpod: {args.riverpod_version}
  provider: 6.1.5+1
  flutter_bloc: 9.1.1
  equatable: 2.1.0
dev_dependencies:
  flutter_test:
    sdk: flutter
"""
        (project / 'pubspec.yaml').write_text(pubspec)
        assemble(project)
        resolve = ['flutter', 'pub', 'get']
        if not args.fetch:
            resolve.append('--offline')
        for command in (resolve, ['flutter', 'analyze', '--no-pub', '--fatal-infos'], ['flutter', 'test', '--no-pub']):
            completed = subprocess.run(command, cwd=project)
            if completed.returncode:
                return completed.returncode
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
