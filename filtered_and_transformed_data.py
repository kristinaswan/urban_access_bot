import geopandas as gpd
import pandas as pd
import warnings

def filtered_and_transformed_data(gdf):
    """
    Очистим геоданные, удалим лишние столбцы, отфильтруем объекты,
    преобразуем полигоны в центроиды и проверим геометрии на повторяющиеся значения.

    Функция предназначена для обработки датасетов, содержащие объекты одного типа POI (Point of interest) из данных OSM (OpenStreetMap)!

    :param gdf: GeoDataFrame содержащий геометрические объекты (точки и полигоны).
    :return: очищенный и трансформированный GeoDataFrame.
    """

    # Шаг 1. Сбрасываем первый уровень индексации
    gdf_dropped_index = gdf.droplevel('element', axis=0).reset_index()

    # Шаг 2. Анализируем пропущенные значения и удаляем столбцы с большим количеством пропусков
    missing_values_ratio = gdf_dropped_index.isna().mean(axis=0) # Анализируем пропущенные значения и рассчитываем их долю
    columns_to_drop = missing_values_ratio[missing_values_ratio > 0.9].index.to_list() # Выбираем столбцы с долей пропусков больше 90%
    if columns_to_drop: # Удаляем выбранные столбцы
        print(f'Удалены столбцы: {", ".join(columns_to_drop)}.')
        gdf_dropped_index.drop(columns=columns_to_drop, inplace=True)
    else:
        print('Столбцов с высоким процентом пропусков не обнаружено.')

    # Шаг 3. Разделяем объекты на точки и полигоны
    points_gdf = gdf_dropped_index[gdf_dropped_index.geom_type == 'Point']
    polygons_gdf = gdf_dropped_index[(gdf_dropped_index.geom_type == "Polygon") | (gdf_dropped_index.geom_type == "MultiPolygon")]
    if not points_gdf.crs.equals(polygons_gdf.crs): # Проверка совпадения систем координат crs. Вывод предупреждения warning, если crs двух датасетов различаются
        warnings.warn("CRS точек и полигонов не совпадает. Для дальнейших преобразований рекомендуется привести датасеты к единому crs.")

    # Шаг 4. Ищем пересечения полигонов с точками (получаем полигоны, содержащие точки)
    intersected_polygons = polygons_gdf.sjoin(points_gdf, how="inner", predicate="contains") # Получаем полигоны, содержащие точки
    poly_indexes_with_points = intersected_polygons.id_left.unique() # Выделяим id полигонов, содержащих точки
    filtered_polygons = polygons_gdf.loc[~polygons_gdf.index.isin(poly_indexes_with_points)] # Оставляем только те полигоны, которые не содержат точки

    # Шаг 5. Создаем итоговый GeoDataFrame, объединяя точки и полигоны без точек
    final_gdf = gpd.GeoDataFrame(pd.concat([points_gdf, filtered_polygons]), crs=gdf.crs)

    # Шаг 6. Преобразуем оставшиеся полигоны в центроиды
    def poly_to_centroid(geom): # Функция для преобразования полигонов в центроиды
        """Преобразуем полигоны в их центроиды."""
        # Если это Polygon, вернем центроид
        if geom.type == 'Polygon':
            return geom.centroid
       # Если это MultiPolygon, вернем список центроидов для каждой его части
        elif geom.type == "MultiPolygon":
            centroids = [part.centroid for part in geom.geoms]
            return centroids
        # Если это Point, оставим как есть
        else:
            return geom

    final_gdf["geometry"] = final_gdf["geometry"].apply(poly_to_centroid) # Преобразуем оставшиеся полигоны в центроиды
    exploded_final_gdf = final_gdf.explode(column="geometry", ignore_index=True) # Преобразуем имеющиеся списки с центроидами в отдельные записи 
    exploded_final_gdf = gpd.GeoDataFrame(exploded_final_gdf, geometry=exploded_final_gdf.geometry, crs="epsg:4326") # Создаем новый GeoDataFrame с обновленными данными и системой координат WGS84

    # Шаг 7. Убедимся, что среди геометрий нет одинаковых значений
    duplicates_count = exploded_final_gdf.geometry.duplicated().sum()
    if duplicates_count > 0:
        print(f"Найдено {duplicates_count} повторяющихся геометрий.")
        exploded_final_gdf = exploded_final_gdf.drop_duplicates(subset=["geometry"])

    return exploded_final_gdf
