package com.cinescope.app.presentation.components

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.LinkAnnotation
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.TextLinkStyles
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.text.withLink
import androidx.compose.ui.unit.dp
import com.cinescope.app.R
import com.cinescope.app.domain.model.AdvisoryCategory
import com.cinescope.app.domain.model.Block
import com.cinescope.app.domain.model.CommunityTopic
import com.cinescope.app.domain.model.ParentsGuide
import com.cinescope.app.domain.model.Severity
import com.cinescope.app.domain.model.SexNudity
import com.cinescope.app.domain.model.VoteBreakdown
import com.cinescope.app.presentation.theme.severityColors
import kotlin.math.roundToInt

private const val PERCENT = 100

/**
 * İçerik hassasiyeti kartı. IMDb (parents guide) ve DTDD (topluluk) blokları birbirinden
 * bağımsız "veri yok" durumuna düşebilir. DTDD attribution'ı kart her göründüğünde, en altta
 * görünür ve tıklanabilir şekilde yer alır (lisans şartı).
 */
@Composable
fun ContentAdvisoryCard(
    parentsGuide: Block<ParentsGuide>,
    community: Block<List<CommunityTopic>>,
    attribution: String,
    modifier: Modifier = Modifier,
) {
    SectionCard(title = stringResource(R.string.advisory_title), modifier = modifier) {
        Text(
            text = stringResource(R.string.advisory_sex_nudity),
            style = MaterialTheme.typography.titleSmall,
        )
        when (parentsGuide) {
            is Block.Missing -> NoDataContent(parentsGuide.reason)
            is Block.Ready -> ParentsGuideContent(parentsGuide.data)
        }

        HorizontalDivider()

        Text(
            text = stringResource(R.string.advisory_community_title),
            style = MaterialTheme.typography.titleSmall,
        )
        when (community) {
            is Block.Missing -> NoDataContent(community.reason)
            is Block.Ready -> CommunityContent(community.data)
        }

        DtddAttribution(text = attribution)
    }
}

@Composable
private fun ParentsGuideContent(guide: ParentsGuide) {
    val sexNudity = guide.sexNudity
    if (sexNudity == null) {
        Text(
            text = stringResource(R.string.advisory_parents_guide_missing),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    } else {
        SexNudityContent(sexNudity)
    }
    if (guide.otherCategories.isNotEmpty()) {
        Text(
            text = stringResource(R.string.advisory_other_categories),
            style = MaterialTheme.typography.labelLarge,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
            guide.otherCategories.forEach { OtherCategoryRow(it) }
        }
    }
}

@Composable
private fun SexNudityContent(data: SexNudity) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        SeverityBadge(data.severity)
        if (data.voteTotal > 0) {
            Text(
                text = stringResource(R.string.advisory_votes_total, data.voteTotal),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
    data.voteBreakdown?.let { VoteBreakdownRows(it) }
    ExpandableDescriptions(items = data.descriptions)
}

@Composable
fun SeverityBadge(severity: Severity?, modifier: Modifier = Modifier) {
    val tone = MaterialTheme.severityColors.of(severity)
    Surface(
        color = tone.container,
        contentColor = tone.onContainer,
        shape = RoundedCornerShape(50),
        modifier = modifier,
    ) {
        Text(
            text = stringResource(severity.labelRes()),
            style = MaterialTheme.typography.labelLarge,
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 4.dp),
        )
    }
}

@Composable
private fun VoteBreakdownRows(breakdown: VoteBreakdown) {
    val colors = MaterialTheme.severityColors
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Severity.entries.forEach { level ->
            val value = breakdown.forSeverity(level)
            val tone = colors.of(level)
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    text = stringResource(level.labelRes()),
                    style = MaterialTheme.typography.bodySmall,
                    modifier = Modifier.width(72.dp),
                )
                LinearProgressIndicator(
                    progress = { value },
                    color = tone.accent,
                    trackColor = MaterialTheme.colorScheme.surfaceVariant,
                    modifier = Modifier
                        .weight(1f)
                        .padding(horizontal = 8.dp),
                )
                Text(
                    text = stringResource(R.string.vote_percent, (value * PERCENT).roundToInt()),
                    style = MaterialTheme.typography.bodySmall,
                    modifier = Modifier.width(44.dp),
                )
            }
        }
    }
}

@Composable
private fun OtherCategoryRow(category: AdvisoryCategory) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        val label = category.type.labelRes()?.let { stringResource(it) } ?: category.rawName
        Text(text = label, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.weight(1f))
        SeverityBadge(category.severity)
    }
}

@Composable
private fun CommunityContent(topics: List<CommunityTopic>) {
    if (topics.isEmpty()) {
        Text(
            text = stringResource(R.string.advisory_community_empty),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        return
    }
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        topics.forEach { CommunityRow(it) }
    }
}

@Composable
private fun CommunityRow(topic: CommunityTopic) {
    val question = topic.key.questionRes()?.let { stringResource(it) } ?: topic.rawQuestion
    Column {
        Text(
            text = stringResource(
                R.string.advisory_community_ratio,
                question,
                (topic.yesRatio * PERCENT).roundToInt(),
            ),
            style = MaterialTheme.typography.bodyMedium,
        )
        Text(
            text = stringResource(R.string.advisory_community_counts, topic.yes, topic.no, topic.commentCount),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        ExpandableDescriptions(
            items = topic.notes,
            showLabel = R.string.notes_show,
            hideLabel = R.string.notes_hide,
        )
    }
}

/** Lisans gereği: tam metin, link'li, görünür. Metin backend'den gelir, yoksa strings.xml. */
@Composable
private fun DtddAttribution(text: String) {
    val url = stringResource(R.string.dtdd_url)
    val label = text.ifBlank { stringResource(R.string.dtdd_attribution) }
    val linkColor = MaterialTheme.colorScheme.primary
    val annotated = buildAnnotatedString {
        withLink(
            LinkAnnotation.Url(
                url = url,
                styles = TextLinkStyles(
                    style = SpanStyle(color = linkColor, textDecoration = TextDecoration.Underline),
                ),
            ),
        ) {
            append(label)
        }
    }
    Text(
        text = annotated,
        style = MaterialTheme.typography.labelMedium,
        modifier = Modifier.padding(top = 4.dp),
    )
}
