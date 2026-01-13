import geopandas as gpd
import pandas as pd

def filtered_and_transformed_data(gdf):
    """
    Очистим геоданные, удалим лишние столбцы, отфильтруем объекты,
    преобразуем полигоны в центроиды и проверим геометрии на повторяющиеся значения.

    :param gdf: GeoDataFrame содержащий геометрические объекты (точки и полигоны).
    :return: очищенный и трансформированный GeoDataFrame.
    """

    # Сбрасываем первый уровень индексации
    gdf_dropped_index = gdf.droplevel('element', axis=0).reset_index()

    # Анализируем пропущенные значения и рассчитываем их долю
    missing_values_ratio = gdf_dropped_index.isna().mean(axis=0)

    # Выбираем столбцы с долей пропусков больше 90%
    columns_to_drop = missing_values_ratio[missing_values_ratio > 0.9].index.to_list()

    # Удаляем выбранные столбцы
    if columns_to_drop:
        print(f'Удалены столбцы: {", ".join(columns_to_drop)}.')
        gdf_dropped_index.drop(columns=columns_to_drop, inplace=True)
    else:
        print('Столбцов с высоким процентом пропусков не обнаружено.')

    # Разделяем объекты на точки и полигоны
    points_gdf = gdf_dropped_index[gdf_dropped_index.geom_type == 'Point']
    polygons_gdf = gdf_dropped_index[gdf_dropped_index.geom_type == 'Polygon']

    # Ищем пересечения полигонов с точками (получаем полигоны, содержащие точки)
    intersected_polygons = polygons_gdf.sjoin(points_gdf, how="inner", predicate="contains")

    # Выделяим индексы полигонов, содержащих точки
    poly_indexes_with_points = intersected_polygons.index_right.unique()

    # Оставляем только те полигоны, которые не содержат точки
    filtered_polygons = polygons_gdf.loc[~polygons_gdf.index.isin(poly_indexes_with_points)]

    # Создаем итоговый GeoDataFrame, объединяя точки и полигоны без точек
    final_gdf = gpd.GeoDataFrame(pd.concat([points_gdf, filtered_polygons]), crs=gdf.crs)

    # Функция для преобразования полигонов в центроиды
    def poly_to_centroid(geom):
        """Преобразуем полигоны в их центроиды."""
        if geom.type == 'Polygon':
            return geom.centroid
        else:
            return geom

    # Преобразуем оставшиеся полигоны в центроиды
    final_gdf["geometry"] = final_gdf["geometry"].apply(poly_to_centroid)

    # Убедимся, что среди геометрий нет одинаковых значений
    duplicates_count = final_gdf.geometry.duplicated().sum()
    if duplicates_count > 0:
        print(f"Найдено {duplicates_count} повторяющихся геометрий.")
        final_gdf = final_gdf.drop_duplicates(subset=["geometry"])

    return final_gdf
