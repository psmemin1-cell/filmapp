package com.cinescope.app.data.remote

import com.cinescope.app.data.remote.dto.MovieSearchResponseDto
import retrofit2.Response
import retrofit2.http.GET
import retrofit2.http.Query

interface CineScopeApi {
    /** 200: sonuç, 404: movie_not_found, 503: TMDB'ye ulaşılamadı. */
    @GET("api/v1/movies/search")
    suspend fun searchMovie(@Query("title") title: String): Response<MovieSearchResponseDto>

    /** Ucuz sağlık kontrolü; uyuyan sunucuyu (ücretsiz barındırma) erkenden uyandırmak için. */
    @GET("health")
    suspend fun health(): Response<Unit>
}
