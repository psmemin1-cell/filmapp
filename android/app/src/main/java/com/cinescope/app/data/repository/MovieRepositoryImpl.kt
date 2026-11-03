package com.cinescope.app.data.repository

import android.util.Log
import com.cinescope.app.data.mapper.toDomain
import com.cinescope.app.data.remote.CineScopeApi
import com.cinescope.app.domain.repository.FailureType
import com.cinescope.app.domain.repository.MovieRepository
import com.cinescope.app.domain.repository.SearchOutcome
import kotlinx.coroutines.CancellationException
import kotlinx.serialization.SerializationException
import java.io.IOException
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class MovieRepositoryImpl @Inject constructor(
    private val api: CineScopeApi,
) : MovieRepository {

    override suspend fun search(title: String): SearchOutcome {
        val started = System.currentTimeMillis()
        return try {
            val response = api.searchMovie(title)
            val elapsed = System.currentTimeMillis() - started
            val body = response.body()
            when {
                response.isSuccessful && body != null -> {
                    Log.d(
                        TAG,
                        "search ok query=\"$title\" status=${response.code()} ${elapsed}ms " +
                            "cached=${body.cached} sources=${body.sources}",
                    )
                    SearchOutcome.Found(body.toDomain())
                }
                response.code() == HTTP_NOT_FOUND -> {
                    Log.d(TAG, "search not_found query=\"$title\" ${elapsed}ms")
                    SearchOutcome.NotFound
                }
                else -> {
                    Log.w(TAG, "search failed query=\"$title\" status=${response.code()} ${elapsed}ms")
                    SearchOutcome.Failure(FailureType.SERVER)
                }
            }
        } catch (e: CancellationException) {
            throw e
        } catch (e: IOException) {
            Log.w(TAG, "search network error query=\"$title\"", e)
            SearchOutcome.Failure(FailureType.NETWORK)
        } catch (e: SerializationException) {
            Log.e(TAG, "search contract mismatch query=\"$title\"", e)
            SearchOutcome.Failure(FailureType.UNKNOWN)
        } catch (e: IllegalArgumentException) {
            Log.e(TAG, "search unexpected payload query=\"$title\"", e)
            SearchOutcome.Failure(FailureType.UNKNOWN)
        }
    }

    override suspend fun warmUp() {
        val started = System.currentTimeMillis()
        try {
            val code = api.health().code()
            Log.d(TAG, "warmUp status=$code ${System.currentTimeMillis() - started}ms")
        } catch (e: CancellationException) {
            throw e
        } catch (e: IOException) {
            Log.d(TAG, "warmUp failed: ${e.message}")
        }
    }

    private companion object {
        const val TAG = "CineScopeRepo"
        const val HTTP_NOT_FOUND = 404
    }
}
