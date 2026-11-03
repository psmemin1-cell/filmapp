package com.cinescope.app.presentation.components

import androidx.annotation.StringRes
import com.cinescope.app.R
import com.cinescope.app.domain.model.AdvisoryCategoryType
import com.cinescope.app.domain.model.CommunityTopicKey
import com.cinescope.app.domain.model.MissingReason
import com.cinescope.app.domain.model.Severity

@StringRes
fun Severity?.labelRes(): Int = when (this) {
    Severity.NONE -> R.string.severity_none
    Severity.MILD -> R.string.severity_mild
    Severity.MODERATE -> R.string.severity_moderate
    Severity.SEVERE -> R.string.severity_severe
    null -> R.string.severity_unknown
}

/** OTHER için null döner; çağıran backend'in özgün adını gösterir. */
@StringRes
fun AdvisoryCategoryType.labelRes(): Int? = when (this) {
    AdvisoryCategoryType.VIOLENCE -> R.string.category_violence
    AdvisoryCategoryType.PROFANITY -> R.string.category_profanity
    AdvisoryCategoryType.ALCOHOL -> R.string.category_alcohol
    AdvisoryCategoryType.FRIGHTENING -> R.string.category_frightening
    AdvisoryCategoryType.OTHER -> null
}

@StringRes
fun CommunityTopicKey.questionRes(): Int? = when (this) {
    CommunityTopicKey.NUDITY -> R.string.community_question_nudity
    CommunityTopicKey.SEX_SCENE -> R.string.community_question_sex_scene
    CommunityTopicKey.SEXUAL_ASSAULT -> R.string.community_question_sexual_assault
    CommunityTopicKey.OTHER -> null
}

@StringRes
fun MissingReason.messageRes(): Int = when (this) {
    MissingReason.UNAVAILABLE -> R.string.block_unavailable
    MissingReason.NOT_FOUND -> R.string.block_not_found
}
