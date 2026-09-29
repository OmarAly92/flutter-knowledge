#!/usr/bin/env python3
"""Build the benchmark fixture projects: a realistic core layer at the paths the skills
name, plus one legacy `orders` feature (and, for drift, a legacy `budget` feature)
that breaks as many conventions as possible, as traps for "legacy never overrides".

Usage: build_fixtures.py <out_dir>
  -> <out_dir>/fixture-drift, <out_dir>/fixture-hive, and the same two projects with
     four core widgets removed (<out_dir>/fixture-drift-nowrap, fixture-hive-nowrap),
     used by the "nowrap" mode to test the missing-wrapper fallback.
  -> <out_dir>/fixture-app (+ -nowrap): the drift project plus a `trips` feature that
     follows the skills, email/phone validators, a legacy mockito test, and the design
     prototype in design/prototype.html (from make_prototype.py). Tasks f1, f2, t1, g1.
  -> <out_dir>/fixture-skin (+ -nowrap): the app project with its AppColors replaced by an
     AppSkin layer (LightSkin/DarkSkin, SkinScope, SkinCubit, AppThemes.fromSkin). Tasks s1, s2.
The drift and hive fixtures must stay byte-identical, or old results stop being comparable.
"""
import os, shutil, sys, textwrap

OUT = sys.argv[1] if __name__ == '__main__' else None
NOWRAP_REMOVED = ('primary_button', 'app_text_field', 'app_loader', 'app_error_widget')


def w(root, path, text):
    p = os.path.join(root, path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w') as f:
        f.write(textwrap.dedent(text).lstrip('\n'))


EN = '''{
  "orders": "Orders",
  "retry": "Retry",
  "save": "Save",
  "somethingWentWrong": "Something went wrong",
  "fieldIsRequired": "This field is required",
  "noInternetConnection": "No internet connection"
}
'''
AR = '''{
  "orders": "الطلبات",
  "retry": "إعادة المحاولة",
  "save": "حفظ",
  "somethingWentWrong": "حدث خطأ ما",
  "fieldIsRequired": "هذا الحقل مطلوب",
  "noInternetConnection": "لا يوجد اتصال بالإنترنت"
}
'''

CORE = {
    # ---------- api ----------
    'lib/core/api/api_consumer.dart': '''
        import 'package:dio/dio.dart';

        abstract class ApiConsumer {
          Future<Response> get(String path, {Map<String, dynamic>? queryParameters});

          Future<Response> post(String path, {Object? body, Map<String, dynamic>? queryParameters});

          Future<Response> put(String path, {Object? body});

          Future<Response> delete(String path, {Object? body});
        }
        ''',
    'lib/core/api/dio_consumer.dart': '''
        import 'package:dio/dio.dart';
        import 'package:app/core/api/api_consumer.dart';
        import 'package:app/core/error_handling/failure.dart';

        class DioConsumer implements ApiConsumer {
          DioConsumer(this._dio);

          final Dio _dio;

          Future<Response> _guard(Future<Response> Function() call) async {
            try {
              return await call();
            } on DioException catch (error) {
              throw ServerFailure.fromDio(error);
            }
          }

          @override
          Future<Response> get(String path, {Map<String, dynamic>? queryParameters}) =>
              _guard(() => _dio.get(path, queryParameters: queryParameters));

          @override
          Future<Response> post(String path, {Object? body, Map<String, dynamic>? queryParameters}) =>
              _guard(() => _dio.post(path, data: body, queryParameters: queryParameters));

          @override
          Future<Response> put(String path, {Object? body}) => _guard(() => _dio.put(path, data: body));

          @override
          Future<Response> delete(String path, {Object? body}) => _guard(() => _dio.delete(path, data: body));
        }
        ''',
    'lib/core/api/api_request_helpers/end_points.dart': '''
        sealed class EndPoints {
          static const String baseUrl = 'https://api.example.com';

          static const String orders = '/orders';
        }
        ''',
    'lib/core/api/global_response.dart': '''
        import 'package:equatable/equatable.dart';

        class GlobalResponse<T> extends Equatable {
          final T? data;
          final String? message;
          final bool? status;

          const GlobalResponse({this.data, this.message, this.status});

          factory GlobalResponse.fromJson(
            Map<String, dynamic> json, {
            T Function(dynamic json)? fromJsonT,
            bool withDataKey = true,
          }) {
            final raw = withDataKey ? json['data'] : json;
            return GlobalResponse(
              data: fromJsonT != null && raw != null ? fromJsonT(raw) : raw as T?,
              message: json['message'] as String?,
              status: json['status'] as bool?,
            );
          }

          @override
          List<Object?> get props => [data, message, status];
        }
        ''',
    'lib/core/network/network_status.dart': '''
        import 'package:connectivity_plus/connectivity_plus.dart';

        abstract class NetworkStatus {
          Future<bool> get isConnected;
        }

        class NetworkStatusImp implements NetworkStatus {
          NetworkStatusImp(this._connectivity);

          final Connectivity _connectivity;

          @override
          Future<bool> get isConnected async {
            final result = await _connectivity.checkConnectivity();
            return !result.contains(ConnectivityResult.none);
          }
        }
        ''',
    # ---------- errors ----------
    'lib/core/error_handling/failure.dart': '''
        import 'package:dio/dio.dart';
        import 'package:equatable/equatable.dart';

        abstract class Failure extends Equatable implements Exception {
          final String message;

          const Failure(this.message);

          @override
          List<Object?> get props => [message];
        }

        class ServerFailure extends Failure {
          const ServerFailure(super.message);

          factory ServerFailure.noNetwork() => const ServerFailure('No internet connection');

          factory ServerFailure.fromDio(DioException error) =>
              ServerFailure(error.message ?? 'Something went wrong');
        }

        class LocalFailure extends Failure {
          const LocalFailure(super.message);

          factory LocalFailure.fromDrift(Object error, StackTrace stackTrace) =>
              LocalFailure(error.toString());

          factory LocalFailure.fromHive(Object error, StackTrace stackTrace) =>
              LocalFailure(error.toString());
        }
        ''',
    'lib/core/error_handling/result.dart': '''
        import 'package:app/core/error_handling/failure.dart';

        typedef FutureResult<T> = Future<Result<T>>;

        sealed class Result<T> {
          const Result();

          factory Result.success(T data) = Success<T>;

          factory Result.failure(Failure failure) = Error<T>;

          R when<R>({
            required R Function(T data) onSuccess,
            required R Function(Failure failure) onFailure,
          }) =>
              switch (this) {
                Success<T>(:final data) => onSuccess(data),
                Error<T>(:final failure) => onFailure(failure),
              };
        }

        final class Success<T> extends Result<T> {
          const Success(this.data);

          final T data;
        }

        final class Error<T> extends Result<T> {
          const Error(this.failure);

          final Failure failure;
        }
        ''',
    # ---------- theme ----------
    'lib/core/app_themes/colors/app_colors.dart': '''
        import 'package:flutter/material.dart';

        sealed class AppColors {
          static const Color primary = Color(0xFF1E6FD9);
          static const Color background = Color(0xFFF7F8FA);
          static const Color surface = Color(0xFFFFFFFF);
          static const Color textPrimary = Color(0xFF1A1C1E);
          static const Color textSecondary = Color(0xFF6B7280);
          static const Color success = Color(0xFF16A34A);
          static const Color warning = Color(0xFFF59E0B);
          static const Color error = Color(0xFFDC2626);
          static const Color divider = Color(0xFFE5E7EB);
        }
        ''',
    'lib/core/app_themes/text_style/app_text_style.dart': '''
        import 'package:flutter/material.dart';
        import 'package:flutter_screenutil/flutter_screenutil.dart';
        import 'package:app/core/app_themes/colors/app_colors.dart';

        sealed class AppTextStyle {
          static TextStyle get style12Regular =>
              TextStyle(fontSize: 12.sp, fontWeight: FontWeight.w400, color: AppColors.textSecondary);
          static TextStyle get style14Regular =>
              TextStyle(fontSize: 14.sp, fontWeight: FontWeight.w400, color: AppColors.textPrimary);
          static TextStyle get style14Medium =>
              TextStyle(fontSize: 14.sp, fontWeight: FontWeight.w500, color: AppColors.textPrimary);
          static TextStyle get style16Medium =>
              TextStyle(fontSize: 16.sp, fontWeight: FontWeight.w500, color: AppColors.textPrimary);
          static TextStyle get style18Bold =>
              TextStyle(fontSize: 18.sp, fontWeight: FontWeight.w700, color: AppColors.textPrimary);
        }
        ''',
    # ---------- helpers ----------
    'lib/core/helpers/localization/locale_keys.g.dart': '''
        // DO NOT EDIT. This is code generated via package:easy_localization/generate.dart

        abstract class LocaleKeys {
          static const orders = 'orders';
          static const retry = 'retry';
          static const save = 'save';
          static const somethingWentWrong = 'somethingWentWrong';
          static const fieldIsRequired = 'fieldIsRequired';
          static const noInternetConnection = 'noInternetConnection';
        }
        ''',
    'lib/core/helpers/extensions/context_extensions.dart': '''
        import 'package:flutter/material.dart';
        import 'package:app/core/app_themes/colors/app_colors.dart';
        import 'package:app/core/widgets/app_text.dart';

        extension ContextExtensions on BuildContext {
          void showSnackBar(String message, {bool isError = true}) {
            ScaffoldMessenger.of(this).showSnackBar(
              SnackBar(
                content: AppText(message),
                backgroundColor: isError ? AppColors.error : AppColors.success,
              ),
            );
          }

          Future<T?> pushNamed<T>(String route, {Object? arguments}) =>
              Navigator.of(this).pushNamed<T>(route, arguments: arguments);

          void pop<T>([T? result]) => Navigator.of(this).pop(result);
        }
        ''',
    'lib/core/helpers/validations/app_form_validations.dart': '''
        import 'package:easy_localization/easy_localization.dart';
        import 'package:app/core/helpers/localization/locale_keys.g.dart';

        sealed class AppFormValidations {
          static String? requiredField(String? value) =>
              (value == null || value.trim().isEmpty) ? LocaleKeys.fieldIsRequired.tr() : null;
        }
        ''',
    # ---------- widgets (no FAB / Card / ListTile wrapper on purpose) ----------
    'lib/core/widgets/app_text.dart': '''
        import 'package:flutter/material.dart';
        import 'package:app/core/app_themes/text_style/app_text_style.dart';

        class AppText extends StatelessWidget {
          const AppText(this.text, {super.key, this.style, this.maxLines, this.textAlign});

          final String text;
          final TextStyle? style;
          final int? maxLines;
          final TextAlign? textAlign;

          @override
          Widget build(BuildContext context) => Text(
                text,
                style: style ?? AppTextStyle.style14Regular,
                maxLines: maxLines,
                overflow: maxLines == null ? null : TextOverflow.ellipsis,
                textAlign: textAlign,
              );
        }
        ''',
    'lib/core/widgets/app_scaffold.dart': '''
        import 'package:flutter/material.dart';
        import 'package:app/core/app_themes/colors/app_colors.dart';

        class AppScaffold extends StatelessWidget {
          const AppScaffold({
            super.key,
            required this.body,
            this.appBar,
            this.floatingActionButton,
            this.bottomNavigationBar,
          });

          final Widget body;
          final PreferredSizeWidget? appBar;
          final Widget? floatingActionButton;
          final Widget? bottomNavigationBar;

          @override
          Widget build(BuildContext context) => Scaffold(
                backgroundColor: AppColors.background,
                appBar: appBar,
                body: SafeArea(child: body),
                floatingActionButton: floatingActionButton,
                bottomNavigationBar: bottomNavigationBar,
              );
        }
        ''',
    'lib/core/widgets/global_appbar.dart': '''
        import 'package:flutter/material.dart';
        import 'package:app/core/app_themes/colors/app_colors.dart';
        import 'package:app/core/app_themes/text_style/app_text_style.dart';

        class GlobalAppbar extends StatelessWidget implements PreferredSizeWidget {
          const GlobalAppbar.main({super.key, required this.titleText, this.actions})
              : showBack = false;

          const GlobalAppbar.sub({super.key, required this.titleText, this.actions})
              : showBack = true;

          final String titleText;
          final List<Widget>? actions;
          final bool showBack;

          @override
          Size get preferredSize => const Size.fromHeight(kToolbarHeight);

          @override
          Widget build(BuildContext context) => AppBar(
                backgroundColor: AppColors.surface,
                automaticallyImplyLeading: showBack,
                title: Text(titleText, style: AppTextStyle.style18Bold),
                actions: actions,
              );
        }
        ''',
    'lib/core/widgets/vertical_space.dart': '''
        import 'package:flutter/material.dart';

        class VerticalSpace extends StatelessWidget {
          const VerticalSpace(this.height, {super.key});

          final double height;

          @override
          Widget build(BuildContext context) => SizedBox(height: height);
        }
        ''',
    'lib/core/widgets/horizontal_space.dart': '''
        import 'package:flutter/material.dart';

        class HorizontalSpace extends StatelessWidget {
          const HorizontalSpace(this.width, {super.key});

          final double width;

          @override
          Widget build(BuildContext context) => SizedBox(width: width);
        }
        ''',
    'lib/core/widgets/primary_button.dart': '''
        import 'package:flutter/material.dart';
        import 'package:app/core/app_themes/colors/app_colors.dart';
        import 'package:app/core/widgets/app_loader.dart';
        import 'package:app/core/widgets/app_text.dart';

        class PrimaryButton extends StatelessWidget {
          const PrimaryButton({super.key, required this.text, required this.onPressed, this.isLoading = false})
              : expand = false;

          const PrimaryButton.expand({super.key, required this.text, required this.onPressed, this.isLoading = false})
              : expand = true;

          final String text;
          final VoidCallback? onPressed;
          final bool isLoading;
          final bool expand;

          @override
          Widget build(BuildContext context) {
            final button = ElevatedButton(
              style: ElevatedButton.styleFrom(backgroundColor: AppColors.primary),
              onPressed: isLoading ? null : onPressed,
              child: isLoading ? const AppLoader(size: 18) : AppText(text),
            );
            return expand ? SizedBox(width: double.infinity, child: button) : button;
          }
        }
        ''',
    'lib/core/widgets/app_text_field.dart': '''
        import 'package:flutter/material.dart';

        class AppTextField extends StatelessWidget {
          const AppTextField({
            super.key,
            this.controller,
            this.hintText,
            this.validator,
            this.maxLines = 1,
            this.keyboardType,
          });

          final TextEditingController? controller;
          final String? hintText;
          final String? Function(String?)? validator;
          final int maxLines;
          final TextInputType? keyboardType;

          @override
          Widget build(BuildContext context) => TextFormField(
                controller: controller,
                validator: validator,
                maxLines: maxLines,
                keyboardType: keyboardType,
                decoration: InputDecoration(hintText: hintText, border: const OutlineInputBorder()),
              );
        }
        ''',
    'lib/core/widgets/app_loader.dart': '''
        import 'package:flutter/material.dart';
        import 'package:app/core/app_themes/colors/app_colors.dart';

        class AppLoader extends StatelessWidget {
          const AppLoader({super.key, this.size = 32});

          final double size;

          @override
          Widget build(BuildContext context) => Center(
                child: SizedBox.square(
                  dimension: size,
                  child: const CircularProgressIndicator(color: AppColors.primary),
                ),
              );
        }
        ''',
    'lib/core/widgets/app_error_widget.dart': '''
        import 'package:easy_localization/easy_localization.dart';
        import 'package:flutter/material.dart';
        import 'package:app/core/helpers/localization/locale_keys.g.dart';
        import 'package:app/core/widgets/app_text.dart';
        import 'package:app/core/widgets/primary_button.dart';
        import 'package:app/core/widgets/vertical_space.dart';

        class AppErrorWidget extends StatelessWidget {
          const AppErrorWidget({super.key, required this.message, this.onRetry});

          final String message;
          final VoidCallback? onRetry;

          @override
          Widget build(BuildContext context) => Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    AppText(message, textAlign: TextAlign.center),
                    if (onRetry != null) ...[
                      const VerticalSpace(12),
                      PrimaryButton(text: LocaleKeys.retry.tr(), onPressed: onRetry),
                    ],
                  ],
                ),
              );
        }
        ''',
    'lib/core/widgets/app_container.dart': '''
        import 'package:flutter/material.dart';
        import 'package:app/core/app_themes/colors/app_colors.dart';

        class AppContainer extends StatelessWidget {
          const AppContainer({super.key, required this.child, this.padding = const EdgeInsets.all(12)});

          final Widget child;
          final EdgeInsetsGeometry padding;

          @override
          Widget build(BuildContext context) => Container(
                padding: padding,
                decoration: BoxDecoration(
                  color: AppColors.surface,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: AppColors.divider),
                ),
                child: child,
              );
        }
        ''',
    # ---------- routing (legacy: private constructor, no BlocProvider in case) ----------
    'lib/core/app_routes/routes_strings.dart': '''
        class RoutesStrings {
          RoutesStrings._();

          static const String orders = '/orders';
        }
        ''',
    'lib/core/app_routes/app_router.dart': '''
        import 'package:flutter/material.dart';
        import 'package:app/core/app_routes/routes_strings.dart';
        import 'package:app/feature/orders/presentation/orders_screen/ui/orders_screen.dart';

        class AppRouter {
          static Route<dynamic>? onGenerateRoute(RouteSettings settings) {
            switch (settings.name) {
              case RoutesStrings.orders:
                return MaterialPageRoute(builder: (_) => const OrdersScreen());
              default:
                return null;
            }
          }
        }
        ''',
    # ---------- legacy orders feature: every file breaks the conventions ----------
    'lib/feature/orders/data/model/order_model.dart': '''
        class OrderModel {
          final String id;
          final String title;
          final double total;

          OrderModel({required this.id, required this.title, required this.total});

          Map<String, dynamic> toJson() => {'id': id, 'title': title, 'total': total};

          factory OrderModel.fromJson(Map<String, dynamic> json) => OrderModel(
                id: json['id'],
                title: json['title'],
                total: (json['total'] as num).toDouble(),
              );
        }
        ''',
    'lib/feature/orders/data/data_source/orders_remote_data_source.dart': '''
        import 'package:app/core/api/api_consumer.dart';
        import 'package:app/core/api/api_request_helpers/end_points.dart';
        import 'package:app/feature/orders/data/model/order_model.dart';

        class OrdersRemoteDataSource {
          OrdersRemoteDataSource(this.api);

          final ApiConsumer api;

          Future<List<OrderModel>> getOrders() async {
            try {
              final response = await api.get(EndPoints.orders);
              return (response.data['data'] as List).map((e) => OrderModel.fromJson(e)).toList();
            } catch (e) {
              print(e);
              rethrow;
            }
          }

          Future<void> cancelOrder(String id) async {
            await api.post('${EndPoints.orders}/$id/cancel');
          }
        }
        ''',
    'lib/feature/orders/data/repository/orders_repository.dart': '''
        import 'package:app/feature/orders/data/data_source/orders_remote_data_source.dart';
        import 'package:app/feature/orders/data/model/order_model.dart';

        class OrdersRepository {
          OrdersRepository(this.remote);

          final OrdersRemoteDataSource remote;

          Future<List<OrderModel>> getOrders() => remote.getOrders();

          Future<void> cancelOrder(String id) => remote.cancelOrder(id);
        }
        ''',
    'lib/feature/orders/presentation/orders_screen/logic/orders_event.dart': '''
        part of 'orders_bloc.dart';

        abstract class OrdersEvent {}

        class LoadOrders extends OrdersEvent {}
        ''',
    'lib/feature/orders/presentation/orders_screen/logic/orders_state.dart': '''
        part of 'orders_bloc.dart';

        abstract class OrdersState {}

        class OrdersInitial extends OrdersState {}

        class OrdersLoading extends OrdersState {}

        class OrdersLoaded extends OrdersState {
          OrdersLoaded(this.orders);

          final List<OrderModel> orders;
        }

        class OrdersError extends OrdersState {
          OrdersError(this.message);

          final String message;
        }
        ''',
    'lib/feature/orders/presentation/orders_screen/logic/orders_bloc.dart': '''
        import 'package:flutter_bloc/flutter_bloc.dart';
        import 'package:app/feature/orders/data/model/order_model.dart';
        import 'package:app/feature/orders/data/repository/orders_repository.dart';

        part 'orders_event.dart';
        part 'orders_state.dart';

        class OrdersBloc extends Bloc<OrdersEvent, OrdersState> {
          OrdersBloc(this.repository) : super(OrdersInitial()) {
            on<LoadOrders>((event, emit) async {
              emit(OrdersLoading());
              try {
                emit(OrdersLoaded(await repository.getOrders()));
              } catch (e) {
                emit(OrdersError(e.toString()));
              }
            });
          }

          final OrdersRepository repository;
        }
        ''',
    'lib/feature/orders/presentation/orders_screen/ui/orders_screen.dart': '''
        import 'package:flutter/material.dart';
        import 'package:flutter_bloc/flutter_bloc.dart';
        import 'package:flutter_screenutil/flutter_screenutil.dart';
        import 'package:app/core/utils/service_locator.dart';
        import 'package:app/feature/orders/presentation/orders_screen/logic/orders_bloc.dart';

        class OrdersScreen extends StatefulWidget {
          const OrdersScreen({super.key});

          @override
          State<OrdersScreen> createState() => _OrdersScreenState();
        }

        class _OrdersScreenState extends State<OrdersScreen> {
          late final OrdersBloc bloc;

          @override
          void initState() {
            super.initState();
            bloc = sl<OrdersBloc>()..add(LoadOrders());
          }

          Widget _buildBody() {
            return BlocBuilder<OrdersBloc, OrdersState>(
              builder: (context, state) {
                if (state is OrdersLoading) {
                  return const Center(child: CircularProgressIndicator());
                }
                if (state is OrdersError) {
                  WidgetsBinding.instance.addPostFrameCallback((_) {
                    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(state.message)));
                  });
                  return const Center(child: Text('Something went wrong'));
                }
                if (state is OrdersLoaded) {
                  return ListView(
                    children: state.orders.map((o) => _OrderTile(title: o.title, total: o.total)).toList(),
                  );
                }
                return const SizedBox();
              },
            );
          }

          @override
          Widget build(BuildContext context) {
            return BlocProvider.value(
              value: bloc,
              child: Scaffold(
                appBar: AppBar(title: const Text('Orders')),
                body: Padding(padding: EdgeInsets.all(16.w), child: _buildBody()),
              ),
            );
          }
        }

        class _OrderTile extends StatelessWidget {
          const _OrderTile({required this.title, required this.total});

          final String title;
          final double total;

          @override
          Widget build(BuildContext context) {
            return Container(
              margin: EdgeInsets.only(bottom: 8.h),
              padding: EdgeInsets.all(12.r),
              color: const Color(0xFFFFFFFF),
              child: Row(
                children: [
                  Expanded(child: Text(title, style: TextStyle(fontSize: 16.sp, fontWeight: FontWeight.bold))),
                  Text('\\$${total.toStringAsFixed(2)}', style: TextStyle(fontSize: 14.sp, color: const Color(0xFF1E6FD9))),
                ],
              ),
            );
          }
        }
        ''',
}

LEGACY_DI_ORDERS = '''
            // orders (legacy inline registrations)
            sl.registerLazySingleton(() => OrdersRemoteDataSource(sl()));
            sl.registerLazySingleton(() => OrdersRepository(sl()));
            sl.registerFactory(() => OrdersBloc(sl()));'''

PUBSPEC = '''
name: app
environment:
  sdk: ^3.5.0
dependencies:
  flutter:
    sdk: flutter
  flutter_bloc: ^9.0.0
  equatable: ^2.0.5
  get_it: ^8.0.0
  easy_localization: ^3.0.7
  talker: ^4.0.0
  dio: ^5.7.0
  connectivity_plus: ^6.0.5
  flutter_screenutil: ^5.9.3
{extra_deps}
dev_dependencies:
  flutter_test:
    sdk: flutter
{extra_dev}
flutter:
  assets:
    - assets/translations/
'''


def common(root):
    for path, text in CORE.items():
        w(root, path, text)
    w(root, 'assets/translations/en.json', EN)
    w(root, 'assets/translations/ar.json', AR)


def drift(root):
    common(root)
    w(root, 'pubspec.yaml', PUBSPEC.format(
        extra_deps='  drift: ^2.20.0\n  drift_flutter: ^0.2.0',
        extra_dev='  drift_dev: ^2.20.0\n  build_runner: ^2.4.0'))
    w(root, 'lib/core/utils/service_locator.dart', '''
        import 'package:connectivity_plus/connectivity_plus.dart';
        import 'package:dio/dio.dart';
        import 'package:get_it/get_it.dart';
        import 'package:app/core/api/api_consumer.dart';
        import 'package:app/core/api/api_request_helpers/end_points.dart';
        import 'package:app/core/api/dio_consumer.dart';
        import 'package:app/core/database/app_database.dart';
        import 'package:app/core/network/network_status.dart';
        import 'package:app/feature/budget/data/data_source/local/budget_local_data_source.dart';
        import 'package:app/feature/orders/data/data_source/orders_remote_data_source.dart';
        import 'package:app/feature/orders/data/repository/orders_repository.dart';
        import 'package:app/feature/orders/presentation/orders_screen/logic/orders_bloc.dart';

        final sl = GetIt.instance;

        class ServiceLocator {
          static Future<void> init() async {
            _coreSetup();
        %s

            // budget (legacy inline registration)
            sl.registerLazySingleton(() => BudgetLocalDataSource(sl()));
          }

          static void _coreSetup() {
            sl.registerLazySingleton<Dio>(() => Dio(BaseOptions(baseUrl: EndPoints.baseUrl)));
            sl.registerLazySingleton<ApiConsumer>(() => DioConsumer(sl()));
            sl.registerLazySingleton<NetworkStatus>(() => NetworkStatusImp(Connectivity()));
            sl.registerLazySingleton<AppDatabase>(() => AppDatabase());
          }
        }
        ''' % LEGACY_DI_ORDERS)
    w(root, 'lib/core/error_handling/drift_error_handler/drift_error_handler.dart', '''
        import 'package:app/core/error_handling/failure.dart';

        extension DriftFutureFailure<T> on Future<T> {
          Future<T> handleLocalFailure() async {
            try {
              return await this;
            } on Failure {
              rethrow;
            } catch (error, stackTrace) {
              throw LocalFailure.fromDrift(error, stackTrace);
            }
          }
        }

        extension DriftStreamFailure<T> on Stream<T> {
          Stream<T> handleLocalFailure() => handleError(
                (Object error, StackTrace stackTrace) => throw LocalFailure.fromDrift(error, stackTrace),
                test: (error) => error is! Failure,
              );
        }
        ''')
    w(root, 'lib/core/database/app_database.dart', '''
        import 'package:drift/drift.dart';
        import 'package:drift_flutter/drift_flutter.dart';
        import 'package:app/core/database/tables/budgets/budgets_dao.dart';
        import 'package:app/core/database/tables/budgets/budgets_table.dart';

        part 'app_database.g.dart';

        @DriftDatabase(tables: [Budgets], daos: [BudgetsDao])
        class AppDatabase extends _$AppDatabase {
          AppDatabase() : super(driftDatabase(name: 'app_db'));

          AppDatabase.forTesting(super.executor);

          @override
          int get schemaVersion => 1;

          @override
          MigrationStrategy get migration => MigrationStrategy(
                onCreate: (m) => m.createAll(),
              );
        }
        ''')
    w(root, 'lib/core/database/tables/budgets/budgets_table.dart', '''
        import 'package:drift/drift.dart';

        @DataClassName('BudgetEntity')
        class Budgets extends Table {
          IntColumn get id => integer().autoIncrement()();
          TextColumn get name => text()();
          RealColumn get amount => real()();
        }
        ''')
    # legacy DAO: no handleLocalFailure
    w(root, 'lib/core/database/tables/budgets/budgets_dao.dart', '''
        import 'package:drift/drift.dart';
        import 'package:app/core/database/app_database.dart';
        import 'package:app/core/database/tables/budgets/budgets_table.dart';

        part 'budgets_dao.g.dart';

        @DriftAccessor(tables: [Budgets])
        class BudgetsDao extends DatabaseAccessor<AppDatabase> with _$BudgetsDaoMixin {
          BudgetsDao(super.db);

          Future<List<BudgetEntity>> getAllBudgets() => select(budgets).get();

          Future<int> insertBudget(BudgetsCompanion entry) => into(budgets).insert(entry);
        }
        ''')
    # legacy budget feature: non-nullable model, params own a drift Companion, concrete data source on AppDatabase
    w(root, 'lib/feature/budget/data/models/budget_model.dart', '''
        import 'package:app/core/database/app_database.dart';

        class BudgetModel {
          final int id;
          final String name;
          final double amount;

          BudgetModel({required this.id, required this.name, required this.amount});

          factory BudgetModel.fromDB(BudgetEntity entity) =>
              BudgetModel(id: entity.id, name: entity.name, amount: entity.amount);
        }
        ''')
    w(root, 'lib/feature/budget/domain/params/add_budget_params.dart', '''
        import 'package:drift/drift.dart';
        import 'package:app/core/database/app_database.dart';

        class AddBudgetParams {
          final String name;
          final double amount;

          AddBudgetParams({required this.name, required this.amount});

          BudgetsCompanion toDb() => BudgetsCompanion.insert(name: name, amount: amount);
        }
        ''')
    w(root, 'lib/feature/budget/data/data_source/local/budget_local_data_source.dart', '''
        import 'package:app/core/database/app_database.dart';
        import 'package:app/feature/budget/data/models/budget_model.dart';
        import 'package:app/feature/budget/domain/params/add_budget_params.dart';

        class BudgetLocalDataSource {
          BudgetLocalDataSource(this._db);

          final AppDatabase _db;

          Future<List<BudgetModel>> getBudgets() async {
            final rows = await _db.budgetsDao.getAllBudgets();
            return rows.map(BudgetModel.fromDB).toList();
          }

          Future<int> addBudget(AddBudgetParams params) => _db.budgetsDao.insertBudget(params.toDb());
        }
        ''')


def hive(root):
    common(root)
    w(root, 'pubspec.yaml', PUBSPEC.format(
        extra_deps='  hive_ce: ^2.10.0\n  hive_ce_flutter: ^2.2.0', extra_dev=''))
    w(root, 'lib/core/utils/service_locator.dart', '''
        import 'package:connectivity_plus/connectivity_plus.dart';
        import 'package:dio/dio.dart';
        import 'package:get_it/get_it.dart';
        import 'package:app/core/api/api_consumer.dart';
        import 'package:app/core/api/api_request_helpers/end_points.dart';
        import 'package:app/core/api/dio_consumer.dart';
        import 'package:app/core/database/hive_boxes.dart';
        import 'package:app/core/network/network_status.dart';
        import 'package:app/feature/orders/data/data_source/orders_remote_data_source.dart';
        import 'package:app/feature/orders/data/repository/orders_repository.dart';
        import 'package:app/feature/orders/presentation/orders_screen/logic/orders_bloc.dart';

        final sl = GetIt.instance;

        class ServiceLocator {
          static Future<void> init() async {
            _coreSetup();
            await initHive();
        %s
          }

          static void _coreSetup() {
            sl.registerLazySingleton<Dio>(() => Dio(BaseOptions(baseUrl: EndPoints.baseUrl)));
            sl.registerLazySingleton<ApiConsumer>(() => DioConsumer(sl()));
            sl.registerLazySingleton<NetworkStatus>(() => NetworkStatusImp(Connectivity()));
          }
        }
        ''' % LEGACY_DI_ORDERS)
    w(root, 'lib/core/database/hive_boxes.dart', '''
        import 'package:hive_ce_flutter/hive_flutter.dart';
        import 'package:app/core/utils/service_locator.dart';

        Future<void> initHive() async {
          await Hive.initFlutter();
          final settingsBox = await Hive.openBox<Map>('settings');
          sl.registerSingleton<Box<Map>>(settingsBox, instanceName: 'settings');
        }
        ''')
    w(root, 'lib/core/error_handling/hive_error_handler/hive_error_handler.dart', '''
        import 'package:app/core/error_handling/failure.dart';

        extension HiveFutureFailure<T> on Future<T> {
          Future<T> handleLocalFailure() async {
            try {
              return await this;
            } on Failure {
              rethrow;
            } catch (error, stackTrace) {
              throw LocalFailure.fromHive(error, stackTrace);
            }
          }
        }

        T handleLocalFailureSync<T>(T Function() op) {
          try {
            return op();
          } on Failure {
            rethrow;
          } catch (error, stackTrace) {
            throw LocalFailure.fromHive(error, stackTrace);
          }
        }
        ''')


# ---------- app fixture: the drift project plus a clean `trips` feature, for tasks f1, f2, t1, g1 ----------
APP_EN = '''{
  "orders": "Orders",
  "trips": "Trips",
  "retry": "Retry",
  "save": "Save",
  "somethingWentWrong": "Something went wrong",
  "fieldIsRequired": "This field is required",
  "enterValidEmail": "Enter a valid email address",
  "enterValidPhone": "Enter a valid phone number",
  "noInternetConnection": "No internet connection"
}
'''
APP_AR = '''{
  "orders": "الطلبات",
  "trips": "الرحلات",
  "retry": "إعادة المحاولة",
  "save": "حفظ",
  "somethingWentWrong": "حدث خطأ ما",
  "fieldIsRequired": "هذا الحقل مطلوب",
  "enterValidEmail": "أدخل بريدًا إلكترونيًا صحيحًا",
  "enterValidPhone": "أدخل رقم هاتف صحيحًا",
  "noInternetConnection": "لا يوجد اتصال بالإنترنت"
}
'''
TRIPS = 'lib/feature/trips/'
TRIPS_SCREEN = TRIPS + 'presentation/trips_screen/'
APP = {
    'lib/core/api/api_request_helpers/end_points.dart': '''
        sealed class EndPoints {
          static const String baseUrl = 'https://api.example.com';

          static const String orders = '/orders';
          static const String trips = '/trips';
        }
        ''',
    'lib/core/app_routes/routes_strings.dart': '''
        class RoutesStrings {
          RoutesStrings._();

          static const String orders = '/orders';
          static const String trips = '/trips';
        }
        ''',
    'lib/core/app_routes/app_router.dart': '''
        import 'package:flutter/material.dart';
        import 'package:flutter_bloc/flutter_bloc.dart';
        import 'package:app/core/app_routes/routes_strings.dart';
        import 'package:app/core/utils/service_locator.dart';
        import 'package:app/feature/orders/presentation/orders_screen/ui/orders_screen.dart';
        import 'package:app/feature/trips/presentation/trips_screen/logic/trips_cubit.dart';
        import 'package:app/feature/trips/presentation/trips_screen/ui/trips_screen.dart';

        class AppRouter {
          static Route<dynamic>? onGenerateRoute(RouteSettings settings) {
            switch (settings.name) {
              case RoutesStrings.orders:
                return MaterialPageRoute(builder: (_) => const OrdersScreen());
              case RoutesStrings.trips:
                return MaterialPageRoute(
                  builder: (context) {
                    return BlocProvider(
                      create: (context) => sl<TripsCubit>(),
                      child: const TripsScreen(),
                    );
                  },
                );
              default:
                return null;
            }
          }
        }
        ''',
    'lib/core/helpers/localization/locale_keys.g.dart': '''
        // DO NOT EDIT. This is code generated via package:easy_localization/generate.dart

        abstract class LocaleKeys {
          static const orders = 'orders';
          static const trips = 'trips';
          static const retry = 'retry';
          static const save = 'save';
          static const somethingWentWrong = 'somethingWentWrong';
          static const fieldIsRequired = 'fieldIsRequired';
          static const enterValidEmail = 'enterValidEmail';
          static const enterValidPhone = 'enterValidPhone';
          static const noInternetConnection = 'noInternetConnection';
        }
        ''',
    'lib/core/helpers/validations/app_form_validations.dart': r'''
        import 'package:easy_localization/easy_localization.dart';
        import 'package:app/core/helpers/localization/locale_keys.g.dart';

        sealed class AppFormValidations {
          static String? requiredField(String? value) =>
              (value == null || value.trim().isEmpty) ? LocaleKeys.fieldIsRequired.tr() : null;

          static String? email(String? value) =>
              (value == null || !RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$').hasMatch(value.trim()))
                  ? LocaleKeys.enterValidEmail.tr()
                  : null;

          static String? phone(String? value) =>
              (value == null || !RegExp(r'^\+?[0-9]{8,15}$').hasMatch(value.trim()))
                  ? LocaleKeys.enterValidPhone.tr()
                  : null;
        }
        ''',
    TRIPS + 'data/model/trip_model.dart': '''
        import 'package:equatable/equatable.dart';

        class TripModel extends Equatable {
          final String? id;
          final String? title;
          final String? destination;
          final String? startDate;
          final double? price;
          final String? contactEmail;
          final String? contactPhone;

          const TripModel({
            this.id,
            this.title,
            this.destination,
            this.startDate,
            this.price,
            this.contactEmail,
            this.contactPhone,
          });

          factory TripModel.fromJson(Map<String, dynamic> json) => TripModel(
                id: json['id'] as String?,
                title: json['title'] as String?,
                destination: json['destination'] as String?,
                startDate: json['start_date'] as String?,
                price: (json['price'] as num?)?.toDouble(),
                contactEmail: json['contact_email'] as String?,
                contactPhone: json['contact_phone'] as String?,
              );

          Map<String, dynamic> toJson() => {
                'id': id,
                'title': title,
                'destination': destination,
                'start_date': startDate,
                'price': price,
                'contact_email': contactEmail,
                'contact_phone': contactPhone,
              };

          @override
          List<Object?> get props => [id, title, destination, startDate, price, contactEmail, contactPhone];
        }
        ''',
    TRIPS + 'data/model/params/get_trips_params.dart': '''
        import 'package:equatable/equatable.dart';

        class GetTripsParams extends Equatable {
          final int page;

          const GetTripsParams({required this.page});

          Map<String, dynamic> toJson() => {'page': page};

          @override
          List<Object?> get props => [page];
        }
        ''',
    TRIPS + 'data/data_source/trips_remote_data_source.dart': '''
        import 'package:app/core/api/api_consumer.dart';
        import 'package:app/core/api/api_request_helpers/end_points.dart';
        import 'package:app/core/api/global_response.dart';
        import 'package:app/feature/trips/data/model/params/get_trips_params.dart';
        import 'package:app/feature/trips/data/model/trip_model.dart';

        abstract class TripsRemoteDataSource {
          Future<GlobalResponse<List<TripModel>>> getTrips(GetTripsParams params);
        }

        class TripsRemoteDataSourceImp implements TripsRemoteDataSource {
          TripsRemoteDataSourceImp(this._apiConsumer);

          final ApiConsumer _apiConsumer;

          @override
          Future<GlobalResponse<List<TripModel>>> getTrips(GetTripsParams params) async {
            final response = await _apiConsumer.get(EndPoints.trips, queryParameters: params.toJson());
            return GlobalResponse.fromJson(
              response.data,
              fromJsonT: (json) => (json as List).map((trip) => TripModel.fromJson(trip)).toList(),
            );
          }
        }
        ''',
    TRIPS + 'data/repository/trips_repository.dart': '''
        import 'package:app/core/api/global_response.dart';
        import 'package:app/core/error_handling/failure.dart';
        import 'package:app/core/error_handling/result.dart';
        import 'package:app/core/network/network_status.dart';
        import 'package:app/feature/trips/data/data_source/trips_remote_data_source.dart';
        import 'package:app/feature/trips/data/model/params/get_trips_params.dart';
        import 'package:app/feature/trips/data/model/trip_model.dart';

        abstract class TripsRepository {
          FutureResult<GlobalResponse<List<TripModel>>> getTrips(GetTripsParams params);
        }

        class TripsRepositoryImp implements TripsRepository {
          TripsRepositoryImp(this._remoteDataSource, this._network);

          final TripsRemoteDataSource _remoteDataSource;
          final NetworkStatus _network;

          @override
          FutureResult<GlobalResponse<List<TripModel>>> getTrips(GetTripsParams params) async {
            if (await _network.isConnected) {
              try {
                final result = await _remoteDataSource.getTrips(params);
                return Result.success(result);
              } on Failure catch (error) {
                return Result.failure(error);
              }
            }
            return Result.failure(ServerFailure.noNetwork());
          }
        }
        ''',
    TRIPS_SCREEN + 'logic/trips_cubit.dart': '''
        import 'package:equatable/equatable.dart';
        import 'package:flutter_bloc/flutter_bloc.dart';
        import 'package:app/core/error_handling/failure.dart';
        import 'package:app/feature/trips/data/model/params/get_trips_params.dart';
        import 'package:app/feature/trips/data/model/trip_model.dart';
        import 'package:app/feature/trips/data/repository/trips_repository.dart';

        part 'trips_state.dart';

        class TripsCubit extends Cubit<TripsState> {
          TripsCubit(this._repository) : super(const TripsInitialState()) {
            getTrips();
          }

          final TripsRepository _repository;

          List<TripModel>? trips;

          Future<void> getTrips() async {
            emit(const GetTripsLoadingState());
            final result = await _repository.getTrips(const GetTripsParams(page: 1));
            result.when(
              onSuccess: (response) {
                trips = response.data;
                emit(const GetTripsSuccessState());
              },
              onFailure: (failure) => emit(GetTripsFailureState(failure: failure)),
            );
          }
        }
        ''',
    TRIPS_SCREEN + 'logic/trips_state.dart': '''
        part of 'trips_cubit.dart';

        sealed class TripsState extends Equatable {
          const TripsState();

          @override
          List<Object?> get props => [];
        }

        final class TripsInitialState extends TripsState {
          const TripsInitialState();
        }

        final class GetTripsLoadingState extends TripsState {
          const GetTripsLoadingState();
        }

        final class GetTripsSuccessState extends TripsState {
          const GetTripsSuccessState();
        }

        final class GetTripsFailureState extends TripsState {
          const GetTripsFailureState({required this.failure});

          final Failure failure;

          @override
          List<Object?> get props => [failure];
        }
        ''',
    TRIPS_SCREEN + 'ui/trips_screen.dart': '''
        import 'package:easy_localization/easy_localization.dart';
        import 'package:flutter/material.dart';
        import 'package:flutter_bloc/flutter_bloc.dart';
        import 'package:app/core/helpers/extensions/context_extensions.dart';
        import 'package:app/core/helpers/localization/locale_keys.g.dart';
        import 'package:app/core/widgets/app_scaffold.dart';
        import 'package:app/core/widgets/global_appbar.dart';
        import 'package:app/feature/trips/presentation/trips_screen/logic/trips_cubit.dart';
        import 'package:app/feature/trips/presentation/trips_screen/ui/widgets/trips_body.dart';

        class TripsScreen extends StatelessWidget {
          const TripsScreen({super.key});

          @override
          Widget build(BuildContext context) => BlocListener<TripsCubit, TripsState>(
                listener: (context, state) {
                  if (state is GetTripsFailureState) {
                    context.showSnackBar(state.failure.message);
                  }
                },
                child: AppScaffold(
                  appBar: GlobalAppbar.main(titleText: LocaleKeys.trips.tr()),
                  body: const TripsBody(),
                ),
              );
        }
        ''',
    TRIPS_SCREEN + 'ui/widgets/trips_body.dart': '''
        import 'package:flutter/material.dart';
        import 'package:flutter_bloc/flutter_bloc.dart';
        import 'package:app/core/widgets/app_error_widget.dart';
        import 'package:app/core/widgets/app_loader.dart';
        import 'package:app/core/widgets/vertical_space.dart';
        import 'package:app/feature/trips/presentation/trips_screen/logic/trips_cubit.dart';
        import 'package:app/feature/trips/presentation/trips_screen/ui/widgets/trip_item.dart';

        class TripsBody extends StatelessWidget {
          const TripsBody({super.key});

          @override
          Widget build(BuildContext context) => BlocBuilder<TripsCubit, TripsState>(
                buildWhen: (previous, current) =>
                    current is GetTripsLoadingState ||
                    current is GetTripsSuccessState ||
                    current is GetTripsFailureState,
                builder: (context, state) {
                  final cubit = context.read<TripsCubit>();
                  return switch (state) {
                    GetTripsFailureState(:final failure) =>
                      AppErrorWidget(message: failure.message, onRetry: cubit.getTrips),
                    GetTripsSuccessState() => ListView.separated(
                        padding: const EdgeInsets.all(16),
                        itemCount: cubit.trips?.length ?? 0,
                        separatorBuilder: (context, index) => const VerticalSpace(12),
                        itemBuilder: (context, index) => TripItem(
                          title: cubit.trips![index].title ?? '',
                          destination: cubit.trips![index].destination ?? '',
                          price: cubit.trips![index].price ?? 0,
                        ),
                      ),
                    _ => const AppLoader(),
                  };
                },
              );
        }
        ''',
    TRIPS_SCREEN + 'ui/widgets/trip_item.dart': '''
        import 'package:flutter/material.dart';
        import 'package:app/core/app_themes/colors/app_colors.dart';
        import 'package:app/core/app_themes/text_style/app_text_style.dart';
        import 'package:app/core/widgets/app_container.dart';
        import 'package:app/core/widgets/app_text.dart';
        import 'package:app/core/widgets/horizontal_space.dart';

        class TripItem extends StatelessWidget {
          const TripItem({super.key, required this.title, required this.destination, required this.price});

          final String title;
          final String destination;
          final double price;

          @override
          Widget build(BuildContext context) => AppContainer(
                child: Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          AppText(title, style: AppTextStyle.style16Medium),
                          AppText(destination, style: AppTextStyle.style12Regular),
                        ],
                      ),
                    ),
                    const HorizontalSpace(12),
                    AppText(
                      '\\$${price.toStringAsFixed(2)}',
                      style: AppTextStyle.style14Medium.copyWith(color: AppColors.primary),
                    ),
                  ],
                ),
              );
        }
        ''',
    # legacy test for the legacy orders feature: flat test/ dir, mockito + codegen
    'test/orders_repository_test.dart': '''
        import 'package:flutter_test/flutter_test.dart';
        import 'package:mockito/annotations.dart';
        import 'package:mockito/mockito.dart';
        import 'package:app/feature/orders/data/data_source/orders_remote_data_source.dart';
        import 'package:app/feature/orders/data/model/order_model.dart';
        import 'package:app/feature/orders/data/repository/orders_repository.dart';

        import 'orders_repository_test.mocks.dart';

        @GenerateMocks([OrdersRemoteDataSource])
        void main() {
          test('getOrders returns the orders from the data source', () async {
            final remote = MockOrdersRemoteDataSource();
            when(remote.getOrders()).thenAnswer((_) async => [OrderModel(id: '1', title: 'Order', total: 10)]);

            final orders = await OrdersRepository(remote).getOrders();

            expect(orders.length, 1);
          });
        }
        ''',
}
TRIPS_DI_CALL = '''
    _tripsFeatureSetup();'''
TRIPS_DI = '''

  static void _tripsFeatureSetup() {
    /// Blocs
    sl.registerFactory<TripsCubit>(() => TripsCubit(sl<TripsRepository>()));

    /// Repository
    sl.registerLazySingleton<TripsRepository>(
      () => TripsRepositoryImp(sl<TripsRemoteDataSource>(), sl<NetworkStatus>()),
    );

    /// Data Sources
    sl.registerLazySingleton<TripsRemoteDataSource>(
      () => TripsRemoteDataSourceImp(sl<ApiConsumer>()),
    );
  }'''
TRIPS_DI_IMPORTS = '''import 'package:app/feature/orders/presentation/orders_screen/logic/orders_bloc.dart';
import 'package:app/feature/trips/data/data_source/trips_remote_data_source.dart';
import 'package:app/feature/trips/data/repository/trips_repository.dart';
import 'package:app/feature/trips/presentation/trips_screen/logic/trips_cubit.dart';'''


def app(root):
    drift(root)
    for path, text in APP.items():
        w(root, path, text)
    w(root, 'assets/translations/en.json', APP_EN)
    w(root, 'assets/translations/ar.json', APP_AR)
    w(root, 'pubspec.yaml', PUBSPEC.format(
        extra_deps='  drift: ^2.20.0\n  drift_flutter: ^0.2.0',
        extra_dev='  drift_dev: ^2.20.0\n  build_runner: ^2.4.0\n  mockito: ^5.4.4'))
    sl_path = os.path.join(root, 'lib/core/utils/service_locator.dart')
    sl = open(sl_path).read()
    sl = sl.replace("import 'package:app/feature/orders/presentation/orders_screen/logic/orders_bloc.dart';", TRIPS_DI_IMPORTS)
    sl = sl.replace('    _coreSetup();', '    _coreSetup();' + TRIPS_DI_CALL)
    sl = sl.replace('  static void _coreSetup() {', TRIPS_DI.lstrip('\n') + '\n\n  static void _coreSetup() {')
    with open(sl_path, 'w') as f:
        f.write(sl)
    design = os.path.join(root, 'design')
    os.makedirs(design, exist_ok=True)
    shutil.copy(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixture_files', 'design', 'prototype.html'), design)


# ---------- skin fixture: the app project with an AppSkin layer instead of AppColors, for tasks s1, s2 ----------
SKIN_DIR = 'lib/core/app_themes/colors/'
SKIN = {
    'lib/core/helpers/cache/cache_keys.dart': '''
        sealed class CacheKeys {
          static const String currentTheme = 'current-theme';
          static const String accessToken = 'access-token';
        }
        ''',
    'lib/core/helpers/cache/cache_helper.dart': '''
        import 'package:shared_preferences/shared_preferences.dart';

        export 'package:app/core/helpers/cache/cache_keys.dart';

        sealed class CacheHelper {
          static late SharedPreferences _preferences;

          static Future<void> init() async => _preferences = await SharedPreferences.getInstance();

          static Object? get(String key) => _preferences.get(key);

          static Future<bool> save(String key, Object value) => switch (value) {
                String v => _preferences.setString(key, v),
                bool v => _preferences.setBool(key, v),
                int v => _preferences.setInt(key, v),
                double v => _preferences.setDouble(key, v),
                _ => throw ArgumentError('Unsupported cache value: $value'),
              };

          static Future<bool> remove(String key) => _preferences.remove(key);
        }
        ''',
    SKIN_DIR + 'app_skin.dart': '''
        import 'package:flutter/material.dart';

        abstract class AppSkin {
          const AppSkin();

          /// The Material [ThemeMode] this skin drives. Example: LightSkin returns
          /// [ThemeMode.light], DarkSkin returns [ThemeMode.dark].
          ThemeMode get themeMode;

          /// The base color of every screen, painted by [AppScaffold] behind all
          /// content. Example: the page behind the trips list.
          Color get background;

          /// The color of blocks sitting on top of [background]. Example: the
          /// card holding one trip in the trips list.
          Color get surface;

          /// A sunken variant of [surface] for blocks that blend with the page.
          /// Example: the tinted fill behind an empty-state illustration.
          Color get card;

          /// The default outline around cards and inputs. Example: the stroke
          /// around a trip card.
          Color get border;

          /// The brand blue used for primary actions and emphasis. Example: the
          /// Save button and the trip price.
          Color get primary;

          /// A readable shade of [primary] for text on [primaryLight] fills.
          /// Example: a label inside a soft brand pill.
          Color get primaryDark;

          /// A soft tint of [primary] used behind brand content. Example: the fill
          /// of a soft brand pill.
          Color get primaryLight;

          /// The sky-blue secondary color for highlights that must not read as
          /// primary. Example: an informational icon on a trip.
          Color get accent;

          /// A soft tint of [accent] used behind accent content. Example: the
          /// square behind an informational icon.
          Color get accentLight;

          /// The strongest text color, for titles. Example: a trip's title.
          Color get textPrimary;

          /// The medium-emphasis text color. Example: a trip's destination.
          Color get textSecondary;

          /// The lowest-emphasis text color, for fine print. Example: a
          /// timestamp under a trip.
          Color get textMuted;

          /// The text color on top of [primary] fills. Example: the Save label.
          Color get textOnPrimary;

          /// The color of a positive outcome. Example: the success snackbar.
          Color get success;

          /// A soft tint of [success] used as a background. Example: the fill of
          /// a confirmed badge.
          Color get successLight;

          /// The color of a failure or destructive state. Example: the error
          /// snackbar.
          Color get error;

          /// A soft tint of [error] used as a background. Example: the fill behind
          /// a destructive action's icon.
          Color get errorLight;

          /// The color of caution. Example: a trip that needs attention.
          Color get warning;

          /// A soft tint of [warning] used as a background. Example: the fill
          /// behind a caution badge.
          Color get warningLight;

          /// The fill of the top app bar. Example: the bar behind 'Trips'.
          Color get appBarBackground => surface;

          /// The title text in the app bar. Example: the 'Trips' title.
          Color get appBarTitle => textPrimary;

          /// Tappable icons in the app bar. Example: the back arrow.
          Color get appBarIcon => textPrimary;

          /// The hairline between rows and around containers. Example: the
          /// outline of [AppContainer].
          Color get divider => border;

          /// The fill of [AppContainer] blocks. Example: a trip card.
          Color get containerBackground => surface;

          /// The fill of [PrimaryButton]. Example: the Save button.
          Color get buttonBackground => primary;

          /// The label color inside [PrimaryButton]. Example: the 'Save' text.
          Color get buttonText => textOnPrimary;

          /// The spinner of [AppLoader]. Example: the loader while trips load.
          Color get loader => primary;

          /// The fill of small rounded label pills. Example: a soft brand pill on
          /// a trip.
          Color get chipBackground => primaryLight;

          /// The text inside those pills. Example: the label in a brand pill.
          Color get chipText => primaryDark;

          /// The background of the success snackbar. Example: 'Trip saved'.
          Color get snackBarSuccess => success;

          /// The background of the error snackbar. Example: 'Something went
          /// wrong'.
          Color get snackBarError => error;

          /// The text inside snackbars. Example: the message on the error bar.
          Color get snackBarText => textOnPrimary;

          /// The dimmed layer behind dialogs and bottom sheets. Example: the scrim
          /// behind a confirmation sheet.
          Color get overlayBarrier => const Color(0x80000000);

          /// The fill of bottom sheets. Example: a confirmation sheet.
          Color get bottomSheetBackground => surface;

          /// The fill of dialogs. Example: a confirmation dialog.
          Color get dialogBackground => surface;
        }
        ''',
    SKIN_DIR + 'light_skin.dart': '''
        import 'package:app/core/app_themes/colors/app_skin.dart';
        import 'package:flutter/material.dart';

        class LightSkin extends AppSkin {
          const LightSkin();

          @override
          ThemeMode get themeMode => ThemeMode.light;

          @override
          Color get background => const Color(0xFFF7F8FA);

          @override
          Color get surface => const Color(0xFFFFFFFF);

          @override
          Color get card => const Color(0xFFF0F2F5);

          @override
          Color get border => const Color(0xFFE5E7EB);

          @override
          Color get primary => const Color(0xFF1E6FD9);

          @override
          Color get primaryDark => const Color(0xFF1553A6);

          @override
          Color get primaryLight => const Color(0xFFE3EEFC);

          @override
          Color get accent => const Color(0xFF0EA5E9);

          @override
          Color get accentLight => const Color(0xFFE0F4FD);

          @override
          Color get textPrimary => const Color(0xFF1A1C1E);

          @override
          Color get textSecondary => const Color(0xFF6B7280);

          @override
          Color get textMuted => const Color(0xFF9CA3AF);

          @override
          Color get textOnPrimary => const Color(0xFFFFFFFF);

          @override
          Color get success => const Color(0xFF16A34A);

          @override
          Color get successLight => const Color(0xFFE3F6EA);

          @override
          Color get error => const Color(0xFFDC2626);

          @override
          Color get errorLight => const Color(0xFFFCE7E7);

          @override
          Color get warning => const Color(0xFFF59E0B);

          @override
          Color get warningLight => const Color(0xFFFEF3DC);
        }
        ''',
    SKIN_DIR + 'dark_skin.dart': '''
        import 'package:app/core/app_themes/colors/app_skin.dart';
        import 'package:flutter/material.dart';

        class DarkSkin extends AppSkin {
          const DarkSkin();

          @override
          ThemeMode get themeMode => ThemeMode.dark;

          @override
          Color get background => const Color(0xFF111316);

          @override
          Color get surface => const Color(0xFF1A1D21);

          @override
          Color get card => const Color(0xFF0C0E10);

          @override
          Color get border => const Color(0x1FFFFFFF);

          @override
          Color get primary => const Color(0xFF5B9BF0);

          @override
          Color get primaryDark => const Color(0xFF9CC3F7);

          @override
          Color get primaryLight => const Color(0x295B9BF0);

          @override
          Color get accent => const Color(0xFF7DD3FC);

          @override
          Color get accentLight => const Color(0x247DD3FC);

          @override
          Color get textPrimary => const Color(0xFFF3F4F6);

          @override
          Color get textSecondary => const Color(0xFFA1A7B0);

          @override
          Color get textMuted => const Color(0xFF6B7280);

          @override
          Color get textOnPrimary => const Color(0xFF0B1220);

          @override
          Color get success => const Color(0xFF4ADE80);

          @override
          Color get successLight => const Color(0x294ADE80);

          @override
          Color get error => const Color(0xFFF87171);

          @override
          Color get errorLight => const Color(0x29F87171);

          @override
          Color get warning => const Color(0xFFFBBF24);

          @override
          Color get warningLight => const Color(0x29FBBF24);

          @override
          Color get bottomSheetBackground => const Color(0xFF23272C);

          @override
          Color get dialogBackground => const Color(0xFF23272C);
        }
        ''',
    SKIN_DIR + 'skin_scope.dart': '''
        import 'package:app/core/app_themes/colors/app_skin.dart';
        import 'package:flutter/material.dart';

        class SkinScope extends InheritedWidget {
          const SkinScope({super.key, required this.skin, required super.child});

          final AppSkin skin;

          static AppSkin of(BuildContext context) {
            final scope = context.dependOnInheritedWidgetOfExactType<SkinScope>();
            assert(scope != null, 'SkinScope not found above this context');
            return scope!.skin;
          }

          @override
          bool updateShouldNotify(SkinScope oldWidget) => skin != oldWidget.skin;
        }

        extension SkinContext on BuildContext {
          AppSkin get skin => SkinScope.of(this);
        }
        ''',
    SKIN_DIR + 'logic/skin_cubit.dart': '''
        import 'package:app/core/app_themes/colors/app_skin.dart';
        import 'package:app/core/app_themes/colors/dark_skin.dart';
        import 'package:app/core/app_themes/colors/light_skin.dart';
        import 'package:app/core/helpers/cache/cache_helper.dart';
        import 'package:equatable/equatable.dart';
        import 'package:flutter/material.dart';
        import 'package:flutter_bloc/flutter_bloc.dart';

        part 'skin_state.dart';

        class SkinCubit extends Cubit<SkinState> {
          SkinCubit() : skin = _savedSkin(), super(const SkinInitialState());

          AppSkin skin;

          static AppSkin _savedSkin() {
            return CacheHelper.get(CacheKeys.currentTheme) == ThemeMode.dark.name
                ? const DarkSkin()
                : const LightSkin();
          }

          void setSkin(AppSkin newSkin) {
            skin = newSkin;
            CacheHelper.save(CacheKeys.currentTheme, newSkin.themeMode.name);
            emit(SkinChangedState(newSkin));
          }

          void toggleSkin() {
            setSkin(skin.themeMode == ThemeMode.dark ? const LightSkin() : const DarkSkin());
          }
        }

        extension SkinSwitcherContext on BuildContext {
          void setSkin(AppSkin skin) => read<SkinCubit>().setSkin(skin);

          void toggleSkin() => read<SkinCubit>().toggleSkin();
        }
        ''',
    SKIN_DIR + 'logic/skin_state.dart': '''
        part of 'skin_cubit.dart';

        sealed class SkinState extends Equatable {
          const SkinState();

          @override
          List<Object?> get props => [];
        }

        final class SkinInitialState extends SkinState {
          const SkinInitialState();
        }

        final class SkinChangedState extends SkinState {
          const SkinChangedState(this.skin);

          final AppSkin skin;

          @override
          List<Object?> get props => [skin];
        }
        ''',
    'lib/core/app_themes/app_motion.dart': '''
        import 'package:flutter/animation.dart';
        import 'package:motor/motor.dart';

        /// Motion tokens mirroring the design's durations, easing curves, and
        /// animation distances. Every animated widget picks from here instead of
        /// inventing its own timing.
        sealed class AppMotion {
          /// Micro interactions: press states, border and color flips on chips
          /// and inputs. Example: a filter chip's border darkening on tap.
          static const Duration fast = Duration(milliseconds: 120);

          /// Standard transitions: fades, background shifts, tab label color.
          /// Example: the primary button fading when it is disabled.
          static const Duration base = Duration(milliseconds: 180);

          /// Entrances of content blocks. Example: a trip card appearing.
          static const Duration slow = Duration(milliseconds: 260);

          /// Big springy morphs. Example: a segmented thumb sliding between
          /// filters.
          static const Duration emphasis = Duration(milliseconds: 450);

          /// One full sweep of the loading shimmer across a placeholder card.
          static const Duration shimmerLoop = Duration(milliseconds: 1400);

          /// The default deceleration curve: fast start, gentle stop. Pairs with
          /// [fast]/[base] for most transitions.
          static const Curve easeOut = Cubic(0.22, 0.61, 0.36, 1);

          /// The symmetric curve for looping animations. Pairs with
          /// [shimmerLoop].
          static const Curve easeInOut = Cubic(0.65, 0, 0.35, 1);

          /// The overshoot curve giving entrances a playful bounce. Pairs with
          /// [slow]/[emphasis] for pops and sheets.
          static const Curve spring = Cubic(0.34, 1.4, 0.64, 1);

          /// How far a fade-up entrance starts below its resting spot. Example:
          /// a form's fields rising 10 into place.
          static const double fadeUpOffset = 10;

          /// How far a sheet-like entrance starts below its resting spot.
          /// Example: the filter sheet rising 60 into place.
          static const double slideUpOffset = 60;

          /// The starting scale of a pop entrance. Example: an empty-state
          /// illustration scaling from 0.94 to full size.
          static const double popScale = 0.94;

          /// The delay before the first item of a staggered group starts.
          static const Duration staggerBase = Duration(milliseconds: 120);

          /// The gap between consecutive items of a staggered group. Example: the
          /// offset between cards popping in on a list.
          static const Duration staggerStep = Duration(milliseconds: 40);

          /// The entrance delay for item [index] of a staggered group. Pass
          /// `leadIn: false` for a list the user is already looking at.
          static Duration staggerAt(int index, {bool leadIn = true}) =>
              (leadIn ? staggerBase : Duration.zero) + staggerStep * index;

          /// Small components reacting to touch: chips, buttons, cards. Example:
          /// a card's press morph.
          static const Motion pressSpring = MaterialSpringMotion.expressiveSpatialFast();

          /// Large surfaces entering. Example: a bottom sheet springing up.
          static const Motion surfaceSpring = MaterialSpringMotion.expressiveSpatialDefault();

          /// Exits and dismissals: quieter, so the overshoot doesn't fight the
          /// gesture that dismissed it. Example: a sheet flung closed.
          static const Motion exitSpring = MaterialSpringMotion.standardSpatialFast();

          /// Non-spatial changes: color, opacity, elevation. Example: a selection
          /// tint settling after a tap.
          static const Motion effectsSpring = MaterialSpringMotion.standardEffectsDefault();
        }
        ''',
    'lib/core/app_themes/themes/app_themes.dart': '''
        import 'package:app/core/app_themes/colors/app_skin.dart';
        import 'package:app/core/app_themes/text_style/app_text_style.dart';
        import 'package:flutter/material.dart';

        sealed class AppThemes {
          static ThemeData fromSkin(AppSkin skin) {
            final brightness = skin.themeMode == ThemeMode.dark ? Brightness.dark : Brightness.light;
            return ThemeData(
              useMaterial3: true,
              brightness: brightness,
              scaffoldBackgroundColor: skin.background,
              appBarTheme: AppBarTheme(
                backgroundColor: skin.appBarBackground,
                titleTextStyle: AppTextStyle.style18Bold.copyWith(color: skin.appBarTitle),
                iconTheme: IconThemeData(color: skin.appBarIcon),
                actionsIconTheme: IconThemeData(color: skin.appBarIcon),
                surfaceTintColor: Colors.transparent,
                elevation: 0,
              ),
              colorScheme: ColorScheme.fromSeed(
                seedColor: skin.primary,
                brightness: brightness,
                primary: skin.primary,
                onPrimary: skin.textOnPrimary,
                primaryContainer: skin.primaryLight,
                onPrimaryContainer: skin.primaryDark,
                secondary: skin.accent,
                onSecondary: skin.textOnPrimary,
                secondaryContainer: skin.accentLight,
                onSecondaryContainer: skin.accent,
                tertiary: skin.accent,
                onTertiary: skin.textOnPrimary,
                tertiaryContainer: skin.accentLight,
                onTertiaryContainer: skin.accent,
                surface: skin.surface,
                onSurface: skin.textPrimary,
                onSurfaceVariant: skin.textSecondary,
                surfaceContainerLowest: skin.card,
                surfaceContainerLow: skin.background,
                surfaceContainer: skin.surface,
                surfaceContainerHigh: skin.surface,
                surfaceContainerHighest: skin.surface,
                outline: skin.border,
                outlineVariant: skin.divider,
                error: skin.error,
                onError: skin.textOnPrimary,
                errorContainer: skin.errorLight,
                onErrorContainer: skin.error,
              ),
              dialogTheme: DialogThemeData(backgroundColor: skin.dialogBackground, barrierColor: skin.overlayBarrier),
              bottomSheetTheme: BottomSheetThemeData(
                backgroundColor: skin.bottomSheetBackground,
                modalBarrierColor: skin.overlayBarrier,
                surfaceTintColor: Colors.transparent,
              ),
              dividerColor: skin.divider,
            );
          }
        }
        ''',
    'lib/my_app.dart': '''
        import 'package:app/core/app_routes/app_router.dart';
        import 'package:app/core/app_routes/routes_strings.dart';
        import 'package:app/core/app_themes/colors/dark_skin.dart';
        import 'package:app/core/app_themes/colors/light_skin.dart';
        import 'package:app/core/app_themes/colors/logic/skin_cubit.dart';
        import 'package:app/core/app_themes/colors/skin_scope.dart';
        import 'package:app/core/app_themes/themes/app_themes.dart';
        import 'package:easy_localization/easy_localization.dart';
        import 'package:flutter/material.dart';
        import 'package:flutter_bloc/flutter_bloc.dart';
        import 'package:flutter_screenutil/flutter_screenutil.dart';

        class MyApp extends StatelessWidget {
          const MyApp({super.key});

          @override
          Widget build(BuildContext context) {
            return MultiBlocProvider(
              providers: [BlocProvider(create: (context) => SkinCubit())],
              child: BlocBuilder<SkinCubit, SkinState>(
                buildWhen: (previous, current) => current is SkinChangedState,
                builder: (context, state) {
                  final skin = context.read<SkinCubit>().skin;
                  return ScreenUtilInit(
                    designSize: const Size(375, 812),
                    minTextAdapt: true,
                    builder: (context, child) => SkinScope(
                      skin: skin,
                      child: MaterialApp(
                        debugShowCheckedModeBanner: false,
                        theme: AppThemes.fromSkin(const LightSkin()),
                        darkTheme: AppThemes.fromSkin(const DarkSkin()),
                        themeMode: skin.themeMode,
                        localizationsDelegates: context.localizationDelegates,
                        supportedLocales: context.supportedLocales,
                        locale: context.locale,
                        onGenerateRoute: AppRouter.onGenerateRoute,
                        initialRoute: RoutesStrings.trips,
                      ),
                    ),
                  );
                },
              ),
            );
          }
        }
        ''',
    'lib/main.dart': '''
        import 'package:app/core/helpers/cache/cache_helper.dart';
        import 'package:app/core/utils/service_locator.dart';
        import 'package:app/my_app.dart';
        import 'package:easy_localization/easy_localization.dart';
        import 'package:flutter/material.dart';

        Future<void> main() async {
          WidgetsFlutterBinding.ensureInitialized();
          await EasyLocalization.ensureInitialized();
          await CacheHelper.init();
          await ServiceLocator.init();
          runApp(
            EasyLocalization(
              supportedLocales: const [Locale('en'), Locale('ar')],
              path: 'assets/translations',
              fallbackLocale: const Locale('en'),
              child: const MyApp(),
            ),
          );
        }
        ''',
    # ---------- the core widgets, reading colors from the skin ----------
    'lib/core/app_themes/text_style/app_text_style.dart': '''
        import 'package:flutter/material.dart';
        import 'package:flutter_screenutil/flutter_screenutil.dart';

        sealed class AppTextStyle {
          static TextStyle get style12Regular => TextStyle(fontSize: 12.sp, fontWeight: FontWeight.w400);
          static TextStyle get style14Regular => TextStyle(fontSize: 14.sp, fontWeight: FontWeight.w400);
          static TextStyle get style14Medium => TextStyle(fontSize: 14.sp, fontWeight: FontWeight.w500);
          static TextStyle get style16Medium => TextStyle(fontSize: 16.sp, fontWeight: FontWeight.w500);
          static TextStyle get style18Bold => TextStyle(fontSize: 18.sp, fontWeight: FontWeight.w700);
        }
        ''',
    'lib/core/widgets/app_text.dart': '''
        import 'package:flutter/material.dart';
        import 'package:app/core/app_themes/colors/skin_scope.dart';
        import 'package:app/core/app_themes/text_style/app_text_style.dart';

        class AppText extends StatelessWidget {
          const AppText(this.text, {super.key, this.style, this.maxLines, this.textAlign});

          final String text;
          final TextStyle? style;
          final int? maxLines;
          final TextAlign? textAlign;

          @override
          Widget build(BuildContext context) {
            final base = style ?? AppTextStyle.style14Regular;
            return Text(
              text,
              style: base.color == null ? base.copyWith(color: context.skin.textPrimary) : base,
              maxLines: maxLines,
              overflow: maxLines == null ? null : TextOverflow.ellipsis,
              textAlign: textAlign,
            );
          }
        }
        ''',
    'lib/core/helpers/extensions/context_extensions.dart': '''
        import 'package:flutter/material.dart';
        import 'package:app/core/app_themes/colors/skin_scope.dart';
        import 'package:app/core/app_themes/text_style/app_text_style.dart';
        import 'package:app/core/widgets/app_text.dart';

        extension ContextExtensions on BuildContext {
          void showSnackBar(String message, {bool isError = true}) {
            ScaffoldMessenger.of(this).showSnackBar(
              SnackBar(
                content: AppText(message, style: AppTextStyle.style14Regular.copyWith(color: skin.snackBarText)),
                backgroundColor: isError ? skin.snackBarError : skin.snackBarSuccess,
              ),
            );
          }

          Future<T?> pushNamed<T>(String route, {Object? arguments}) =>
              Navigator.of(this).pushNamed<T>(route, arguments: arguments);

          void pop<T>([T? result]) => Navigator.of(this).pop(result);
        }
        ''',
    'lib/core/widgets/app_scaffold.dart': '''
        import 'package:flutter/material.dart';
        import 'package:app/core/app_themes/colors/skin_scope.dart';

        class AppScaffold extends StatelessWidget {
          const AppScaffold({
            super.key,
            required this.body,
            this.appBar,
            this.floatingActionButton,
            this.bottomNavigationBar,
          });

          final Widget body;
          final PreferredSizeWidget? appBar;
          final Widget? floatingActionButton;
          final Widget? bottomNavigationBar;

          @override
          Widget build(BuildContext context) => Scaffold(
                backgroundColor: context.skin.background,
                appBar: appBar,
                body: SafeArea(child: body),
                floatingActionButton: floatingActionButton,
                bottomNavigationBar: bottomNavigationBar,
              );
        }
        ''',
    'lib/core/widgets/global_appbar.dart': '''
        import 'package:flutter/material.dart';
        import 'package:app/core/app_themes/colors/skin_scope.dart';
        import 'package:app/core/app_themes/text_style/app_text_style.dart';

        class GlobalAppbar extends StatelessWidget implements PreferredSizeWidget {
          const GlobalAppbar.main({super.key, required this.titleText, this.actions})
              : showBack = false;

          const GlobalAppbar.sub({super.key, required this.titleText, this.actions})
              : showBack = true;

          final String titleText;
          final List<Widget>? actions;
          final bool showBack;

          @override
          Size get preferredSize => const Size.fromHeight(kToolbarHeight);

          @override
          Widget build(BuildContext context) => AppBar(
                backgroundColor: context.skin.appBarBackground,
                automaticallyImplyLeading: showBack,
                title: Text(titleText, style: AppTextStyle.style18Bold.copyWith(color: context.skin.appBarTitle)),
                actions: actions,
              );
        }
        ''',
    'lib/core/widgets/primary_button.dart': '''
        import 'package:flutter/material.dart';
        import 'package:app/core/app_themes/colors/skin_scope.dart';
        import 'package:app/core/app_themes/text_style/app_text_style.dart';
        import 'package:app/core/app_themes/app_motion.dart';
        import 'package:app/core/widgets/app_loader.dart';
        import 'package:app/core/widgets/app_text.dart';

        class PrimaryButton extends StatelessWidget {
          const PrimaryButton({super.key, required this.text, required this.onPressed, this.isLoading = false, this.backgroundColor})
              : expand = false;

          const PrimaryButton.expand({super.key, required this.text, required this.onPressed, this.isLoading = false, this.backgroundColor})
              : expand = true;

          final String text;
          final VoidCallback? onPressed;
          final bool isLoading;
          final bool expand;
          final Color? backgroundColor;

          @override
          Widget build(BuildContext context) {
            final button = ElevatedButton(
              style: ElevatedButton.styleFrom(backgroundColor: backgroundColor ?? context.skin.buttonBackground),
              onPressed: isLoading ? null : onPressed,
              child: isLoading
                  ? const AppLoader(size: 18)
                  : AppText(text, style: AppTextStyle.style14Medium.copyWith(color: context.skin.buttonText)),
            );
            final faded = AnimatedOpacity(
              duration: AppMotion.base,
              curve: AppMotion.easeOut,
              opacity: onPressed == null ? 0.6 : 1,
              child: button,
            );
            return expand ? SizedBox(width: double.infinity, child: faded) : faded;
          }
        }
        ''',
    'lib/core/widgets/app_loader.dart': '''
        import 'package:flutter/material.dart';
        import 'package:app/core/app_themes/colors/skin_scope.dart';

        class AppLoader extends StatelessWidget {
          const AppLoader({super.key, this.size = 32});

          final double size;

          @override
          Widget build(BuildContext context) => Center(
                child: SizedBox.square(
                  dimension: size,
                  child: CircularProgressIndicator(color: context.skin.loader),
                ),
              );
        }
        ''',
    'lib/core/widgets/app_container.dart': '''
        import 'package:flutter/material.dart';
        import 'package:app/core/app_themes/colors/skin_scope.dart';

        class AppContainer extends StatelessWidget {
          const AppContainer({super.key, required this.child, this.padding = const EdgeInsets.all(12)});

          final Widget child;
          final EdgeInsetsGeometry padding;

          @override
          Widget build(BuildContext context) => Container(
                padding: padding,
                decoration: BoxDecoration(
                  color: context.skin.containerBackground,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: context.skin.divider),
                ),
                child: child,
              );
        }
        ''',
    TRIPS_SCREEN + 'ui/widgets/trip_item.dart': '''
        import 'package:flutter/material.dart';
        import 'package:app/core/app_themes/colors/skin_scope.dart';
        import 'package:app/core/app_themes/text_style/app_text_style.dart';
        import 'package:app/core/widgets/app_container.dart';
        import 'package:app/core/widgets/app_text.dart';
        import 'package:app/core/widgets/horizontal_space.dart';

        class TripItem extends StatelessWidget {
          const TripItem({super.key, required this.title, required this.destination, required this.price});

          final String title;
          final String destination;
          final double price;

          @override
          Widget build(BuildContext context) => AppContainer(
                child: Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          AppText(title, style: AppTextStyle.style16Medium),
                          AppText(
                            destination,
                            style: AppTextStyle.style12Regular.copyWith(color: context.skin.textSecondary),
                          ),
                        ],
                      ),
                    ),
                    const HorizontalSpace(12),
                    AppText(
                      '\\$${price.toStringAsFixed(2)}',
                      style: AppTextStyle.style14Medium.copyWith(color: context.skin.primary),
                    ),
                  ],
                ),
              );
        }
        ''',
}


def skin(root):
    app(root)
    os.remove(os.path.join(root, 'lib/core/app_themes/colors/app_colors.dart'))
    shutil.rmtree(os.path.join(root, 'design'))
    for path, text in SKIN.items():
        w(root, path, text)
    w(root, 'pubspec.yaml', PUBSPEC.format(
        extra_deps='  drift: ^2.20.0\n  drift_flutter: ^0.2.0\n  shared_preferences: ^2.3.2\n  motor: ^1.1.0',
        extra_dev='  drift_dev: ^2.20.0\n  build_runner: ^2.4.0\n  mockito: ^5.4.4'))


def nowrap(src, dst):
    shutil.copytree(src, dst)
    for name in NOWRAP_REMOVED:
        os.remove(os.path.join(dst, 'lib/core/widgets', name + '.dart'))


if __name__ == '__main__':
    for engine, build in (('drift', drift), ('hive', hive), ('app', app), ('skin', skin)):
        root = os.path.join(OUT, 'fixture-' + engine)
        for d in (root, root + '-nowrap'):
            shutil.rmtree(d, ignore_errors=True)
        build(root)
        nowrap(root, root + '-nowrap')
    print('fixtures written to', OUT)
