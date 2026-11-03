package com.cinescope.app.data.mapper

import com.cinescope.app.data.remote.dto.MovieSearchResponseDto
import com.cinescope.app.domain.model.AdvisoryCategoryType
import com.cinescope.app.domain.model.Block
import com.cinescope.app.domain.model.CommunityTopicKey
import com.cinescope.app.domain.model.MissingReason
import com.cinescope.app.domain.model.Severity
import kotlinx.serialization.json.Json
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class MovieMapperTest {

    private val json = Json {
        ignoreUnknownKeys = true
        explicitNulls = false
        coerceInputValues = true
    }

    private fun parse(body: String) = json.decodeFromString<MovieSearchResponseDto>(body).toDomain()

    @Test
    fun `full contract maps to ready blocks`() {
        val result = parse(FULL)
        assertEquals("tmdb", result.movie.ratingSource)
        assertEquals(181, result.movie.runtimeMinutes)
        val streaming = result.streaming as Block.Ready
        assertEquals("Netflix", streaming.data.flatrate.single().name)
        val guide = (result.parentsGuide as Block.Ready).data
        assertEquals(Severity.MODERATE, guide.sexNudity?.severity)
        assertEquals(0.44f, guide.sexNudity?.voteBreakdown?.moderate)
        assertEquals(AdvisoryCategoryType.VIOLENCE, guide.otherCategories.single().type)
        val community = (result.community as Block.Ready).data.single()
        assertEquals(CommunityTopicKey.NUDITY, community.key)
        val similar = result.similar as Block.Ready
        assertTrue(similar.isFallback)
        assertEquals("Powered by DoesTheDogDie.com", result.attribution)
    }

    @Test
    fun `sources status and nullability are checked together`() {
        val result = parse(DEGRADED)
        // streaming_tr null olsa da tmdb "ok" -> yine veri yok
        assertEquals(Block.Missing(MissingReason.UNAVAILABLE), result.streaming)
        assertEquals(Block.Missing(MissingReason.UNAVAILABLE), result.parentsGuide)
        assertEquals(Block.Missing(MissingReason.NOT_FOUND), result.community)
        assertEquals(Block.Missing(MissingReason.NOT_FOUND), result.similar)
    }

    @Test
    fun `unknown severity maps to null`() {
        assertEquals(null, "Extreme".toSeverity())
        assertEquals(Severity.NONE, "None".toSeverity())
    }

    private companion object {
        val FULL = """
            {"query":"oppenheimer",
             "movie":{"tmdb_id":872585,"imdb_id":"tt15398776","title":"Oppenheimer",
               "original_title":"Oppenheimer","year":2023,"runtime_minutes":181,"overview":"...",
               "poster_url":"https://image.tmdb.org/t/p/w500/x.jpg","rating":8.1,
               "rating_source":"tmdb","rating_votes":7421},
             "streaming_tr":{"available":true,"flatrate":[{"name":"Netflix","logo_url":"https://image.tmdb.org/t/p/w92/x.jpg"}],
               "rent":[],"buy":[],"tmdb_link":"https://www.themoviedb.org/movie/872585/watch?locale=TR"},
             "content_advisory":{
               "sex_nudity":{"severity":"Moderate","vote_total":412,
                 "vote_breakdown":{"none":0.12,"mild":0.21,"moderate":0.44,"severe":0.23},
                 "descriptions":["a","b"]},
               "other_categories":[{"name":"Violence & Gore","severity":"Mild","vote_total":388}],
               "community":[{"topic_id":108,"topic_key":"nudity","question":"Is there nudity?","yes":184,"no":31,
                 "yes_ratio":0.856,"comment_count":12,"notes":["n"]}],
               "attribution":"Powered by DoesTheDogDie.com"},
             "similar":[{"tmdb_id":335984,"title":"Blade Runner 2049","year":2017,
               "poster_url":"https://image.tmdb.org/t/p/w342/x.jpg","rating":7.6}],
             "sources":{"tmdb":"ok","imdb_parents_guide":"ok","dtdd":"ok","similar":"fallback"},
             "cached":false,"generated_at":"2026-11-03T12:04:11Z"}
        """.trimIndent()

        val DEGRADED = """
            {"query":"x",
             "movie":{"tmdb_id":1,"title":"X","rating_source":"tmdb"},
             "streaming_tr":null,
             "content_advisory":null,
             "similar":null,
             "sources":{"tmdb":"ok","imdb_parents_guide":"unavailable","dtdd":"not_found","similar":"not_found"},
             "cached":true,"generated_at":"2026-11-03T12:04:11Z"}
        """.trimIndent()
    }
}
