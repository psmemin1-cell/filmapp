package com.cinescope.app.presentation.search

import com.cinescope.app.domain.repository.FailureType
import com.cinescope.app.domain.repository.MovieRepository
import com.cinescope.app.domain.repository.SearchOutcome
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceTimeBy
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class SearchViewModelTest {

    private val dispatcher = StandardTestDispatcher()

    private class FakeRepository(var outcome: SearchOutcome = SearchOutcome.NotFound) : MovieRepository {
        val queries = mutableListOf<String>()
        override suspend fun search(title: String): SearchOutcome {
            queries += title
            return outcome
        }
    }

    @Before
    fun setUp() = Dispatchers.setMain(dispatcher)

    @After
    fun tearDown() = Dispatchers.resetMain()

    @Test
    fun `typing is debounced by 400 ms`() = runTest(dispatcher) {
        val repo = FakeRepository()
        val vm = SearchViewModel(repo)
        advanceUntilIdle()
        vm.onQueryChange("opp")
        advanceTimeBy(200)
        vm.onQueryChange("oppen")
        advanceTimeBy(399)
        assertTrue(repo.queries.isEmpty())
        advanceTimeBy(2)
        advanceUntilIdle()
        assertEquals(listOf("oppen"), repo.queries)
        assertEquals(SearchUiState.NotFound("oppen"), vm.uiState.value)
    }

    @Test
    fun `keyboard search skips debounce`() = runTest(dispatcher) {
        val repo = FakeRepository()
        val vm = SearchViewModel(repo)
        advanceUntilIdle()
        vm.onQueryChange("Oppenheimer")
        vm.onSearch()
        advanceTimeBy(1)
        assertEquals(listOf("Oppenheimer"), repo.queries)
        advanceUntilIdle()
        assertEquals(1, repo.queries.size) // debounce aynı metni tekrar aramaz
    }

    @Test
    fun `failure exposes error and retry re-runs`() = runTest(dispatcher) {
        val repo = FakeRepository(SearchOutcome.Failure(FailureType.NETWORK))
        val vm = SearchViewModel(repo)
        advanceUntilIdle()
        vm.onQueryChange("Dune")
        vm.onSearch()
        advanceUntilIdle()
        assertEquals(SearchUiState.Error("Dune", FailureType.NETWORK), vm.uiState.value)
        vm.onRetry()
        advanceUntilIdle()
        assertEquals(listOf("Dune", "Dune"), repo.queries)
    }

    @Test
    fun `clear returns to idle`() = runTest(dispatcher) {
        val vm = SearchViewModel(FakeRepository())
        advanceUntilIdle()
        vm.onQueryChange("Dune")
        vm.onSearch()
        advanceUntilIdle()
        vm.onClear()
        advanceUntilIdle()
        assertEquals(SearchUiState.Idle, vm.uiState.value)
        assertEquals("", vm.query.value)
    }
}
